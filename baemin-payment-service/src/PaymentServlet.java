import java.io.*;
import java.net.*;
import java.sql.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import jakarta.servlet.*;
import jakarta.servlet.http.*;

public class PaymentServlet extends HttpServlet {
    private static final String DB_HOST = System.getenv().getOrDefault("PG_HOST", "msa-payment-db");
    private static final String DB_PORT = System.getenv().getOrDefault("PG_PORT", "5432");
    private static final String DB_USER = System.getenv().getOrDefault("PG_USER", "payment_user");
    private static final String DB_PASS = System.getenv().getOrDefault("PG_PASSWORD", "payment_pass");
    private static final String DB_NAME = System.getenv().getOrDefault("PG_DATABASE", "paymentdb");
    private static final String REDIS_HOST = System.getenv().getOrDefault("REDIS_HOST", "redis-queue");
    private static final int REDIS_PORT = Integer.parseInt(System.getenv().getOrDefault("REDIS_PORT", "6379"));

    private static String hostname = "payment-tomcat";

    @Override
    public void init() throws ServletException {
        try {
            hostname = InetAddress.getLocalHost().getHostName();
        } catch (Exception ignored) {}

        // 1. Init Database in background thread
        new Thread(this::initDBAndWorker).start();
    }

    private Connection getDbConnection() throws SQLException {
        String url = "jdbc:postgresql://" + DB_HOST + ":" + DB_PORT + "/" + DB_NAME;
        return DriverManager.getConnection(url, DB_USER, DB_PASS);
    }

    private void initDBAndWorker() {
        int retries = 15;
        while (retries > 0) {
            try (Connection conn = getDbConnection(); Statement stmt = conn.createStatement()) {
                stmt.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id SERIAL PRIMARY KEY,
                        order_no VARCHAR(50) NOT NULL UNIQUE,
                        amount INT NOT NULL,
                        pay_method VARCHAR(30) NOT NULL,
                        status VARCHAR(30) NOT NULL,
                        processed_by VARCHAR(50) NOT NULL,
                        approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """);
                System.out.println("[" + hostname + "] Apache Tomcat 10: PostgreSQL payment-db connected.");
                break;
            } catch (Exception e) {
                System.out.println("Waiting for PostgreSQL payment-db (" + retries + " left): " + e.getMessage());
                retries--;
                try { Thread.sleep(2000); } catch (Exception ignored) {}
            }
        }

        // 2. Start Redis Order Consumer Thread
        startRedisConsumer();
    }

    private void startRedisConsumer() {
        new Thread(() -> {
            System.out.println("[" + hostname + "] Starting Tomcat Java Background Redis Consumer...");
            while (true) {
                try (Socket socket = new Socket(REDIS_HOST, REDIS_PORT);
                     OutputStream out = socket.getOutputStream();
                     BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream()))) {

                    // Simple Redis BLPOP order_queue 3 (Raw RESP protocol)
                    while (true) {
                        String cmd = "*3\r\n$5\r\nBLPOP\r\n$11\r\norder_queue\r\n$1\r\n3\r\n";
                        out.write(cmd.getBytes());
                        out.flush();

                        String line = reader.readLine();
                        if (line == null) break;
                        if (line.startsWith("*2")) { // 2 array elements: queue name, value
                            reader.readLine(); // $11
                            reader.readLine(); // order_queue
                            reader.readLine(); // $length
                            String jsonVal = reader.readLine(); // order json payload

                            processOrderPayment(jsonVal);
                        }
                    }
                } catch (Exception e) {
                    try { Thread.sleep(2000); } catch (Exception ignored) {}
                }
            }
        }).start();
    }

    private void processOrderPayment(String jsonPayload) {
        try {
            // Quick regex/string extract for lightweight execution without huge jackson jar
            String orderNo = "BM-" + System.currentTimeMillis();
            int amount = 20000;

            int oIdx = jsonPayload.indexOf("\"orderNo\":");
            if (oIdx != -1) {
                int start = jsonPayload.indexOf("\"", oIdx + 10) + 1;
                int end = jsonPayload.indexOf("\"", start);
                orderNo = jsonPayload.substring(start, end);
            }

            int aIdx = jsonPayload.indexOf("\"totalAmount\":");
            if (aIdx != -1) {
                int start = aIdx + 14;
                int end = start;
                while (end < jsonPayload.length() && Character.isDigit(jsonPayload.charAt(end))) end++;
                if (start < end) {
                    amount = Integer.parseInt(jsonPayload.substring(start, end));
                }
            }

            try (Connection conn = getDbConnection();
                 PreparedStatement pstmt = conn.prepareStatement(
                     "INSERT INTO payments (order_no, amount, pay_method, status, processed_by) VALUES (?, ?, ?, ?, ?) ON CONFLICT (order_no) DO NOTHING")) {
                pstmt.setString(1, orderNo);
                pstmt.setInt(2, amount);
                pstmt.setString(3, "배민페이 (간편결제)");
                pstmt.setString(4, "PAYMENT_APPROVED");
                pstmt.setString(5, hostname);
                pstmt.executeUpdate();
            }

            // Publish to payment_events via simple redis PUBLISH
            try (Socket pubSocket = new Socket(REDIS_HOST, REDIS_PORT);
                 OutputStream pubOut = pubSocket.getOutputStream()) {
                String eventJson = "{\"orderNo\":\"" + orderNo + "\",\"status\":\"PAID\",\"processedBy\":\"" + hostname + "\"}";
                String pubCmd = "*3\r\n$7\r\nPUBLISH\r\n$14\r\npayment_events\r\n$" + eventJson.getBytes().length + "\r\n" + eventJson + "\r\n";
                pubOut.write(pubCmd.getBytes());
                pubOut.flush();
            }

            System.out.println("💳 [Tomcat 10 / Java 17] Payment Approved for Order " + orderNo + " (" + amount + " KRW) by " + hostname);
        } catch (Exception e) {
            System.err.println("Payment processing error: " + e.getMessage());
        }
    }

    @Override
    protected void doOptions(HttpServletRequest req, HttpServletResponse resp) {
        setCORSHeaders(resp);
        resp.setStatus(HttpServletResponse.SC_OK);
    }

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        setCORSHeaders(resp);
        resp.setContentType("application/json;charset=UTF-8");

        String path = req.getRequestURI();
        if (path.endsWith("/health")) {
            boolean dbOk = false;
            try (Connection conn = getDbConnection()) {
                dbOk = conn.isValid(2);
            } catch (Exception ignored) {}

            String json = String.format(
                "{\"service\":\"payment-service\",\"language\":\"Java 17 (Apache Tomcat 10.1)\",\"status\":\"UP\",\"hostname\":\"%s\",\"database\":\"PostgreSQL 15 (msa-payment-db)\",\"dbStatus\":\"%s\",\"redisQueue\":\"CONNECTED\",\"port\":8083}",
                hostname, dbOk ? "CONNECTED" : "DISCONNECTED"
            );
            resp.getWriter().write(json);
            return;
        }

        if (path.endsWith("/history")) {
            StringBuilder sb = new StringBuilder("[");
            try (Connection conn = getDbConnection();
                 PreparedStatement pstmt = conn.prepareStatement("SELECT order_no, amount, pay_method, status, processed_by, approved_at FROM payments ORDER BY id DESC LIMIT 15");
                 ResultSet rs = pstmt.executeQuery()) {
                boolean first = true;
                while (rs.next()) {
                    if (!first) sb.append(",");
                    first = false;
                    sb.append(String.format(
                        "{\"orderNo\":\"%s\",\"amount\":%d,\"payMethod\":\"%s\",\"status\":\"%s\",\"processedBy\":\"%s\",\"approvedAt\":\"%s\"}",
                        rs.getString("order_no"), rs.getInt("amount"), rs.getString("pay_method"),
                        rs.getString("status"), rs.getString("processed_by"), rs.getString("approved_at")
                    ));
                }
            } catch (Exception e) {
                resp.setStatus(500);
                resp.getWriter().write("{\"error\":\"" + e.getMessage() + "\"}");
                return;
            }
            sb.append("]");
            resp.getWriter().write(sb.toString());
            return;
        }

        if (path.endsWith("/reset")) {
            resetPayments(resp);
            return;
        }

        resp.getWriter().write("{\"message\":\"Tomcat 10 Payment Service Running\"}");
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        setCORSHeaders(resp);
        resp.setContentType("application/json;charset=UTF-8");
        String path = req.getRequestURI();
        if (path.endsWith("/reset")) {
            resetPayments(resp);
            return;
        }
        resp.getWriter().write("{\"message\":\"Tomcat 10 Payment Service Running\"}");
    }

    private void resetPayments(HttpServletResponse resp) throws IOException {
        try (Connection conn = getDbConnection(); Statement stmt = conn.createStatement()) {
            stmt.execute("TRUNCATE TABLE payments RESTART IDENTITY;");
            resp.getWriter().write("{\"success\":true,\"message\":\"Payment DB Cleared\"}");
        } catch (Exception e) {
            resp.setStatus(500);
            resp.getWriter().write("{\"success\":false,\"error\":\"" + e.getMessage() + "\"}");
        }
    }

    private void setCORSHeaders(HttpServletResponse resp) {
        resp.setHeader("Access-Control-Allow-Origin", "*");
        resp.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        resp.setHeader("Access-Control-Allow-Headers", "*");
    }
}
