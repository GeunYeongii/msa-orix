<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Orix Capital - 리스 현황</title>
    <style>
        body { font-family: sans-serif; background-color: #e6f2ff; text-align: center; padding: 50px; }
        .container { background: white; padding: 40px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-top: 5px solid #007bff; }
        h1 { color: #003366; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; }
        th { background-color: #f2f2f2; }
        .home-btn { display: inline-block; margin-top: 30px; padding: 10px 20px; background-color: #003366; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 내 리스 현황 (Lease Service)</h1>
        <p>이 페이지는 <strong>msa-lease</strong> 컨테이너(Tomcat 8.5)에서 독립적으로 렌더링된 화면입니다.</p>
        <table>
            <tr><th>리스 상품명</th><th>계약번호</th><th>월 납입금</th></tr>
            <tr><td>GV80 장기렌터카</td><td>L-2026-001</td><td>850,000 원</td></tr>
            <tr><td>벤츠 S클래스 운용리스</td><td>L-2026-042</td><td>2,150,000 원</td></tr>
        </table>
        <a href="/" class="home-btn">⬅️ 메인 포털로 돌아가기</a>
    </div>
</body>
</html>
