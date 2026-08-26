FROM nginx:alpine

# 복사 1: 프론트엔드 정적 파일들을 Nginx의 기본 웹 호스팅 디렉토리로 복사
COPY index.html /usr/share/nginx/html/index.html
COPY style.css /usr/share/nginx/html/style.css

# 복사 2: 리버스 프록시(API-GW로 보내는 설정)가 담긴 커스텀 설정 파일을 복사
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
