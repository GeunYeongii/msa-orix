import http.server
import socketserver
import json
import time

PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Allow a slight delay to simulate real network request
        time.sleep(0.5)
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        data = {
            "status": "success",
            "service": "lease",
            "data": [
                {"leaseName": "GV80 장기렌터카", "contractNo": "L-2026-001", "monthlyFee": "850,000"},
                {"leaseName": "벤츠 S클래스 운용리스", "contractNo": "L-2026-042", "monthlyFee": "2,150,000"}
            ]
        }
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Lease Service starting on port {PORT}...")
    httpd.serve_forever()
