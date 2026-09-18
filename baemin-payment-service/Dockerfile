FROM tomcat:10.1-jdk17-temurin-jammy

# 1. Change Tomcat port from 8080 to 8083
RUN sed -i 's/port="8080"/port="8083"/g' /usr/local/tomcat/conf/server.xml

# 2. Download PostgreSQL JDBC Driver to Tomcat common lib
RUN curl -o /usr/local/tomcat/lib/postgresql.jar https://jdbc.postgresql.org/download/postgresql-42.7.3.jar

# 3. Setup webapp ROOT directory
RUN rm -rf /usr/local/tomcat/webapps/ROOT/*
COPY WEB-INF /usr/local/tomcat/webapps/ROOT/WEB-INF/
COPY src/PaymentServlet.java /tmp/PaymentServlet.java

# 4. Compile Servlet using Tomcat's servlet-api.jar and postgresql.jar
RUN mkdir -p /usr/local/tomcat/webapps/ROOT/WEB-INF/classes && \
    javac -cp "/usr/local/tomcat/lib/*" -d /usr/local/tomcat/webapps/ROOT/WEB-INF/classes /tmp/PaymentServlet.java

EXPOSE 8083
CMD ["catalina.sh", "run"]
