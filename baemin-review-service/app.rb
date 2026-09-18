require 'sinatra'
require 'rack/cors'
require 'mongo'
require 'json'
require 'socket'

set :bind, '0.0.0.0'
set :port, 8085
set :server, :puma

use Rack::Cors do
  allow do
    origins '*'
    resource '*', headers: :any, methods: [:get, :post, :options]
  end
end

HOSTNAME = Socket.gethostname
MONGO_HOST = ENV['MONGO_HOST'] || 'msa-review-db'
MONGO_PORT = ENV['MONGO_PORT'] || '27017'
MONGO_DB   = ENV['MONGO_DATABASE'] || 'reviewdb'

Mongo::Logger.logger.level = Logger::WARN
$client = nil

def get_mongo_collection
  if $client.nil?
    retries = 10
    while retries > 0
      begin
        $client = Mongo::Client.new(["#{MONGO_HOST}:#{MONGO_PORT}"], database: MONGO_DB, connect_timeout: 3)
        $client.database.command(ping: 1)
        puts "[#{HOSTNAME}] Connected to MongoDB review-db successfully."
        seed_reviews_if_empty($client[:reviews])
        break
      rescue => e
        puts "Waiting for MongoDB... (#{retries} left): #{e.message}"
        retries -= 1
        sleep 2
      end
    end
  end
  $client[:reviews] if $client
end

def seed_reviews_if_empty(coll)
  if coll.count_documents == 0
    puts "[#{HOSTNAME}] Seeding initial reviews into MongoDB (NoSQL)..."
    sample_reviews = [
      { store_id: 1, author: "배민미식가", rating: 5, content: "바삭바삭 튀김옷과 육즙이 최고입니다! 황금올리브치킨 감동이에요.", date: "2026-09-18", created_at: Time.now },
      { store_id: 1, author: "강남치킨러", rating: 5, content: "배달도 20분만에 오고 따뜻해서 맛있게 먹었습니다.", date: "2026-09-17", created_at: Time.now },
      { store_id: 2, author: "떡볶이러버", rating: 5, content: "역시 엽떡은 오리지널 매운맛이 진리입니다. 스트레스 다 풀림!", date: "2026-09-18", created_at: Time.now },
      { store_id: 2, author: "치즈폭포", rating: 4, content: "모둠튀김이랑 로제떡볶이 조합 환상입니다 ㅎㅎ", date: "2026-09-16", created_at: Time.now },
      { store_id: 3, author: "버거매니아", rating: 5, content: "쉑버거 패티 육즙 가득하고 빵이 너무 부드러워요.", date: "2026-09-18", created_at: Time.now },
      { store_id: 4, author: "스시덕후", rating: 5, content: "특선 모둠초밥 구성 알차고 연어 싱싱함이 대박입니다.", date: "2026-09-18", created_at: Time.now }
    ]
    coll.insert_many(sample_reviews)
  end
end

# Ensure DB connection on start
Thread.new { get_mongo_collection }

get '/health' do
  content_type :json
  coll = get_mongo_collection
  status_db = coll ? 'CONNECTED' : 'DISCONNECTED'
  {
    service: 'review-service',
    language: 'Ruby 3.2 (Sinatra)',
    status: 'UP',
    hostname: HOSTNAME,
    database: 'MongoDB 6 NoSQL (msa-review-db)',
    dbStatus: status_db,
    port: 8085
  }.to_json
end

get '/review/list' do
  content_type :json
  store_id = params['storeId'] ? params['storeId'].to_i : nil
  coll = get_mongo_collection
  return [].to_json unless coll

  query = store_id ? { store_id: store_id } : {}
  docs = coll.find(query).sort(created_at: -1).limit(30).to_a

  results = docs.map do |d|
    {
      id: d['_id'].to_s,
      storeId: d['store_id'],
      author: d['author'],
      rating: d['rating'],
      content: d['content'],
      date: d['date'] || d['created_at'].to_s[0..9],
      createdAt: d['date'] || d['created_at'].to_s[0..9]
    }
  end
  { reviews: results, totalCount: results.length }.to_json
end

get '/review/store/:id' do
  content_type :json
  store_id = params[:id].to_i
  coll = get_mongo_collection
  return { reviews: [], totalCount: 0 }.to_json unless coll

  docs = coll.find(store_id: store_id).sort(created_at: -1).limit(30).to_a
  results = docs.map do |d|
    {
      id: d['_id'].to_s,
      storeId: d['store_id'],
      author: d['author'],
      rating: d['rating'],
      content: d['content'],
      date: d['date'] || d['created_at'].to_s[0..9],
      createdAt: d['date'] || d['created_at'].to_s[0..9]
    }
  end
  { reviews: results, totalCount: results.length }.to_json
end

post '/review/create' do
  content_type :json
  raw_body = request.body.read
  payload = begin
    JSON.parse(raw_body)
  rescue
    {}
  end
  coll = get_mongo_collection

  return { success: false, message: 'DB not ready' }.to_json unless coll

  store_id = payload['storeId'] ? payload['storeId'].to_i : 1
  author = payload['author'] || '배민고객'
  rating = payload['rating'] ? payload['rating'].to_i : 5
  content = payload['content'] || '맛있게 잘 먹었습니다!'

  new_doc = {
    store_id: store_id,
    author: author,
    rating: rating,
    content: content,
    date: Time.now.strftime("%Y-%m-%d"),
    created_at: Time.now
  }
  res = coll.insert_one(new_doc)

  {
    success: true,
    message: 'MongoDB에 리뷰가 성공적으로 등록되었습니다.',
    reviewId: res.inserted_id.to_s
  }.to_json
end

['/reset', '/review/reset'].each do |path|
  get path do
    reset_reviews
  end
  post path do
    reset_reviews
  end
end

def reset_reviews
  content_type :json
  coll = get_mongo_collection
  return { success: false, message: 'DB not ready' }.to_json unless coll

  coll.delete_many({})
  seed_reviews_if_empty(coll)
  { success: true, message: 'Review DB Reset to Initial Seed' }.to_json
end
