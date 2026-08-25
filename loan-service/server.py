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
            "service": "loan",
            "data": [
                {"productName": "대출 A", "interestRate": "연 4.5%", "limit": "잔액 12,000,000원"},
                {"productName": "대출 B", "interestRate": "연 5.2%", "limit": "잔액 35,500,000원"}
            ]
        }
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Loan Service starting on port {PORT}...")
    httpd.serve_forever()
