import http.server
import socketserver

PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        html_content = """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>Orix Capital - 환율 정보</title>
            <style>
                body { font-family: sans-serif; background-color: #f2e6ff; text-align: center; padding: 50px; }
                .container { background: white; padding: 40px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-top: 5px solid #6f42c1; }
                h1 { color: #4a2b82; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 12px; }
                th { background-color: #f2f2f2; }
                .home-btn { display: inline-block; margin-top: 30px; padding: 10px 20px; background-color: #6f42c1; color: white; text-decoration: none; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>💱 실시간 환율 정보 (Exchange Service)</h1>
                <p>이 페이지는 <strong>msa-exchange</strong> 컨테이너에서 독립적으로 렌더링된 화면입니다.</p>
                <table>
                    <tr><th>통화명</th><th>매매기준율</th><th>전일대비</th></tr>
                    <tr><td>USD (미국)</td><td>1,342.50</td><td style="color:red;">+2.10</td></tr>
                    <tr><td>EUR (유럽)</td><td>1,455.20</td><td style="color:blue;">-1.40</td></tr>
                    <tr><td>JPY (일본 100)</td><td>905.30</td><td style="color:red;">+5.20</td></tr>
                </table>
                <a href="/" class="home-btn">⬅️ 메인 포털로 돌아가기</a>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html_content.encode('utf-8'))

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Exchange Service starting on port {PORT}...")
    httpd.serve_forever()
