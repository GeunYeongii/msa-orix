<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Orix Capital - 대출 현황</title>
    <style>
        body { font-family: sans-serif; background-color: #e6ffe6; text-align: center; padding: 50px; }
        .container { background: white; padding: 40px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-top: 5px solid #28a745; }
        h1 { color: #1e7e34; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; }
        th { background-color: #f2f2f2; }
        .home-btn { display: inline-block; margin-top: 30px; padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 내 대출 현황 (Loan Service)</h1>
        <p>이 페이지는 <strong>msa-loan</strong> 컨테이너(Tomcat 9.0)에서 독립적으로 렌더링된 화면입니다.</p>
        <table>
            <tr><th>대출 상품명</th><th>적용 금리</th><th>대출 잔액</th></tr>
            <tr><td>대출 A</td><td>연 4.5%</td><td>12,000,000 원</td></tr>
            <tr><td>대출 B</td><td>연 5.2%</td><td>35,500,000 원</td></tr>
        </table>
        <a href="/" class="home-btn">⬅️ 메인 포털로 돌아가기</a>
    </div>
</body>
</html>
