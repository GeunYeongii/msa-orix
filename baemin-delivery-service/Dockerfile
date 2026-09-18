FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY . .
RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -o delivery-service main.go

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/delivery-service .
EXPOSE 8084
CMD ["./delivery-service"]
