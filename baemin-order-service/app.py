import pymysql
import json
import os
import time
import uuid
import socket
from flask import Flask, request, jsonify
from flask_cors import CORS
import redis

app = Flask(__name__)
CORS(app)

DB_HOST = os.environ.get("MYSQL_HOST", "msa-order-db")
DB_PORT = int(os.environ.get("MYSQL_PORT", 3306))
DB_USER = os.environ.get("MYSQL_USER", "order_user")
DB_PASS = os.environ.get("MYSQL_PASSWORD", "order_pass")
DB_NAME = os.environ.get("MYSQL_DATABASE", "orderdb")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis-queue")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
HOSTNAME = socket.gethostname()

def get_redis():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
        return r
    except Exception as e:
        print(f"Redis Connection Failed: {e}")
        return None

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=3
    )

def init_db():
    retries = 15
    while retries > 0:
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_no VARCHAR(60) NOT NULL UNIQUE,
                        store_name VARCHAR(100) NOT NULL,
                        items_json TEXT NOT NULL,
                        total_amount INT NOT NULL,
                        status VARCHAR(40) NOT NULL,
                        processed_by VARCHAR(60),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
            conn.commit()
            conn.close()
            print(f"[{HOSTNAME}] Connected to MariaDB order-db successfully.")
            break
        except Exception as e:
            print(f"Waiting for MariaDB... ({retries} left): {e}")
            retries -= 1
            time.sleep(2)

@app.route('/health', methods=['GET'])
def health():
    db_status = "DISCONNECTED"
    try:
        conn = get_db_connection()
        conn.ping(reconnect=True)
        conn.close()
        db_status = "CONNECTED"
    except Exception as e:
        pass

    r = get_redis()
    redis_status = "CONNECTED" if r else "DISCONNECTED"
    return jsonify({
        "service": "order-service",
        "language": "Python 3.11 (Flask High-Concurrency)",
        "status": "UP",
        "hostname": HOSTNAME,
        "database": "MariaDB 10 (MySQL Engine - msa-order-db)",
        "dbStatus": db_status,
        "redisQueue": redis_status,
        "port": 8082
    })

@app.route('/order/create', methods=['POST'])
def create_order():
    data = request.json or {}
    store_name = data.get("storeName", "배민 인기 맛집")
    items = data.get("items", [])
    total_amount = data.get("totalAmount", 0)

    order_no = f"BM-{int(time.time())}-{uuid.uuid4().hex[:4].upper()}"

    # 1. Save to MariaDB (order-db)
    order_id = 0
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO orders (order_no, store_name, items_json, total_amount, status, processed_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (order_no, store_name, json.dumps(items, ensure_ascii=False), total_amount, "ORDER_RECEIVED", HOSTNAME))
            order_id = cur.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"MariaDB Insert Failed: {e}")
        return jsonify({"success": False, "message": f"MariaDB 에러: {e}"}), 500

    # 2. Loose Coupling: Push Event to Redis Message Queue
    event_payload = {
        "orderId": order_id,
        "orderNo": order_no,
        "storeName": store_name,
        "items": items,
        "totalAmount": total_amount,
        "processedBy": HOSTNAME,
        "timestamp": time.time()
    }

    r = get_redis()
    queue_pushed = False
    if r:
        try:
            r.rpush("order_queue", json.dumps(event_payload, ensure_ascii=False))
            r.publish("order_events", json.dumps(event_payload, ensure_ascii=False))

            # Push to Notification Queue for notification-service
            notif_payload = {
                "orderNo": order_no,
                "storeName": store_name,
                "message": f"[{store_name}] 주문이 성공적으로 접수되었습니다! ({total_amount:,}원)",
                "type": "ORDER_CREATED",
                "timestamp": time.time()
            }
            r.rpush("notification_queue", json.dumps(notif_payload, ensure_ascii=False))
            queue_pushed = True
        except Exception as e:
            print(f"Failed to publish to redis: {e}")

    return jsonify({
        "success": True,
        "orderNo": order_no,
        "orderId": order_id,
        "status": "ORDER_RECEIVED",
        "processedBy": HOSTNAME,
        "eventQueuePushed": queue_pushed,
        "message": f"주문이 성공적으로 접수되었습니다. (처리 서버: {HOSTNAME})"
    })

@app.route('/order/list', methods=['GET'])
def list_orders():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, order_no, store_name, items_json, total_amount, status, processed_by, created_at FROM orders ORDER BY id DESC LIMIT 20")
            rows = cur.fetchall()
        conn.close()

        orders = []
        for r in rows:
            orders.append({
                "id": r["id"],
                "orderNo": r["order_no"],
                "storeName": r["store_name"],
                "items": json.loads(r["items_json"]),
                "totalAmount": r["total_amount"],
                "status": r["status"],
                "processedBy": r["processed_by"],
                "createdAt": str(r["created_at"])
            })
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/order/reset', methods=['GET', 'POST'])
@app.route('/reset', methods=['GET', 'POST'])
def reset_orders():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE orders;")
        conn.commit()
        conn.close()

        r = get_redis()
        if r:
            r.delete("order_queue", "notification_queue")

        return jsonify({"success": True, "message": "Order DB & Redis Queues Cleared"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8082)
