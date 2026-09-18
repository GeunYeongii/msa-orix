import psycopg2
import json
import os
import time
import socket
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import redis

app = Flask(__name__)
CORS(app)

DB_HOST = os.environ.get("PG_HOST", "msa-notification-db")
DB_PORT = int(os.environ.get("PG_PORT", 5432))
DB_USER = os.environ.get("PG_USER", "notif_user")
DB_PASS = os.environ.get("PG_PASSWORD", "notif_pass")
DB_NAME = os.environ.get("PG_DATABASE", "notifdb")

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
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
        connect_timeout=3
    )

def init_db():
    retries = 15
    while retries > 0:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    order_no VARCHAR(60) NOT NULL,
                    recipient VARCHAR(60) NOT NULL,
                    message TEXT NOT NULL,
                    status VARCHAR(30) NOT NULL,
                    sent_by VARCHAR(60),
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            conn.close()
            print(f"[{HOSTNAME}] Connected to PostgreSQL notification-db successfully.")
            break
        except Exception as e:
            print(f"Waiting for PostgreSQL notification-db... ({retries} left): {e}")
            retries -= 1
            time.sleep(2)

# Background Worker: Pulls notifications from notification_queue
def redis_notification_consumer():
    print(f"[{HOSTNAME}] Starting Notification Consumer Daemon...")
    while True:
        try:
            r = get_redis()
            if not r:
                time.sleep(2)
                continue

            # Blocking pop with 3s timeout
            item = r.blpop("notification_queue", timeout=3)
            if item:
                queue_name, data_str = item
                event = json.loads(data_str)
                order_no = event.get("orderNo", "BM-UNKNOWN")
                message = event.get("message", "주문 알림이 도착했습니다.")

                # Save to PostgreSQL notification-db
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO notifications (order_no, recipient, message, status, sent_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (order_no, "010-1234-5678 (고객님)", message, "ALIMTALK_SENT", HOSTNAME))
                conn.commit()
                conn.close()

                print(f"🔔 [Notification Sent] Order {order_no}: {message} (Worker: {HOSTNAME})")
        except Exception as e:
            time.sleep(2)

@app.route('/health', methods=['GET'])
def health():
    db_status = "DISCONNECTED"
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        db_status = "CONNECTED"
    except:
        pass

    r = get_redis()
    redis_status = "CONNECTED" if r else "DISCONNECTED"
    pending_count = 0
    if r:
        try:
            pending_count = r.llen("notification_queue")
        except:
            pass

    return jsonify({
        "service": "notification-service",
        "language": "Python 3.10 (Async Worker)",
        "status": "UP",
        "hostname": HOSTNAME,
        "database": "PostgreSQL 15 (msa-notification-db)",
        "dbStatus": db_status,
        "redisQueue": redis_status,
        "pendingInQueue": pending_count,
        "port": 8086
    })

@app.route('/notification/list', methods=['GET'])
def list_notifications():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, order_no, recipient, message, status, sent_by, to_char(sent_at, 'YYYY-MM-DD HH24:MI:SS') FROM notifications ORDER BY id DESC LIMIT 20")
        rows = cur.fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "id": r[0], "orderNo": r[1], "recipient": r[2],
                "message": r[3], "status": r[4], "sentBy": r[5], "sentAt": r[6]
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notification/pending', methods=['GET'])
def get_pending():
    r = get_redis()
    count = 0
    if r:
        try:
            count = r.llen("notification_queue")
        except:
            pass
    return jsonify({"pendingCount": count})

@app.route('/notification/reset', methods=['GET', 'POST'])
@app.route('/reset', methods=['GET', 'POST'])
def reset_notifications():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE notifications RESTART IDENTITY;")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Notification DB Reset"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    init_db()
    t = threading.Thread(target=redis_notification_consumer, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=8086)
