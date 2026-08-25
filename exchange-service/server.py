import http.server
import socketserver
import json
import time

PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        time.sleep(0.5)
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        data = {
            "status": "success",
            "service": "exchange",
            "data": [
                {"currency": "USD (미국)", "rate": "1,342.50", "change": "+2.10"},
                {"currency": "EUR (유럽)", "rate": "1,455.20", "change": "-1.40"},
                {"currency": "JPY (일본 100)", "rate": "905.30", "change": "+5.20"}
            ]
        }
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Exchange Service starting on port {PORT}...")
    httpd.serve_forever()
