package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

type DeliveryStatus struct {
	OrderNo    string `json:"orderNo"`
	RiderName  string `json:"riderName"`
	RiderPhone string `json:"riderPhone"`
	Status     string `json:"status"`
	EtaMinutes int    `json:"etaMinutes"`
	UpdatedBy  string `json:"updatedBy"`
	UpdatedAt  string `json:"updatedAt"`
}

var (
	ctx          = context.Background()
	rdb          *redis.Client
	hostname     string
	latestMu     sync.RWMutex
	latestStatus = DeliveryStatus{
		OrderNo:    "BM-INITIAL",
		RiderName:  "배민라이더 박준영",
		RiderPhone: "010-9988-7766",
		Status:     "배달 대기중",
		EtaMinutes: 25,
		UpdatedBy:  "delivery-pod",
		UpdatedAt:  time.Now().Format("2006-01-02 15:04:05"),
	}
	riders = []string{"배민라이더 김철수", "배민라이더 이민호", "배민라이더 박준영", "배민1 한상우"}
)

func init() {
	var err error
	hostname, err = os.Hostname()
	if err != nil {
		hostname = "delivery-go-worker"
	}
	latestStatus.UpdatedBy = hostname

	redisHost := os.Getenv("REDIS_HOST")
	if redisHost == "" {
		redisHost = "redis-queue"
	}
	redisPort := os.Getenv("REDIS_PORT")
	if redisPort == "" {
		redisPort = "6379"
	}

	rdb = redis.NewClient(&redis.Options{
		Addr: fmt.Sprintf("%s:%s", redisHost, redisPort),
	})
}

func redisWorker() {
	log.Printf("[%s] Starting Go Goroutine Redis Consumer...", hostname)
	pubsub := rdb.Subscribe(ctx, "payment_events", "order_events")
	defer pubsub.Close()

	ch := pubsub.Channel()
	for msg := range ch {
		var payload map[string]interface{}
		if err := json.Unmarshal([]byte(msg.Payload), &payload); err == nil {
			orderNo, _ := payload["orderNo"].(string)
			if orderNo == "" {
				orderNo = "BM-UNKNOWN"
			}

			rider := riders[rand.Intn(len(riders))]
			eta := 20 + rand.Intn(15)

			latestMu.Lock()
			latestStatus = DeliveryStatus{
				OrderNo:    orderNo,
				RiderName:  rider,
				RiderPhone: "010-9988-7766",
				Status:     "음식 픽업 완료 ➔ 배달 출발",
				EtaMinutes: eta,
				UpdatedBy:  hostname,
				UpdatedAt:  time.Now().Format("2006-01-02 15:04:05"),
			}
			latestMu.Unlock()

			log.Printf("🛵 [Go Delivery Worker] Order %s Assigned to %s (ETA: %d mins)", orderNo, rider, eta)
		}
	}
}

func enableCORS(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "*")
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	if r.Method == http.MethodOptions {
		return
	}

	redisStatus := "CONNECTED"
	if err := rdb.Ping(ctx).Err(); err != nil {
		redisStatus = "DISCONNECTED"
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"service":    "delivery-service",
		"language":   "Go 1.22 (Golang Goroutines)",
		"status":     "UP",
		"hostname":   hostname,
		"database":   "Redis In-Memory State & PubSub",
		"redisQueue": redisStatus,
		"port":       8084,
	})
}

func trackHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	if r.Method == http.MethodOptions {
		return
	}

	latestMu.RLock()
	defer latestMu.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(latestStatus)
}

func resetHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(w)
	if r.Method == http.MethodOptions {
		return
	}

	latestMu.Lock()
	latestStatus = DeliveryStatus{
		OrderNo:    "BM-INITIAL",
		RiderName:  "배민라이더 박준영",
		RiderPhone: "010-9988-7766",
		Status:     "배달 대기중",
		EtaMinutes: 25,
		UpdatedBy:  hostname,
		UpdatedAt:  time.Now().Format("2006-01-02 15:04:05"),
	}
	latestMu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Delivery State Reset to Initial",
	})
}

func main() {
	go redisWorker()

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/delivery/track", trackHandler)
	http.HandleFunc("/delivery/reset", resetHandler)
	http.HandleFunc("/reset", resetHandler)

	port := ":8084"
	log.Printf("[Delivery-Service] Go 1.22 server starting on port %s...", port)
	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
