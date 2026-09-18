const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const os = require('os');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = 8081;
const HOSTNAME = os.hostname();

const pool = new Pool({
  host: process.env.PG_HOST || 'msa-store-db',
  port: parseInt(process.env.PG_PORT || '5432'),
  user: process.env.PG_USER || 'store_user',
  password: process.env.PG_PASSWORD || 'store_pass',
  database: process.env.PG_DATABASE || 'storedb',
  connectionTimeoutMillis: 5000
});

const sampleStores = [
  {
    name: "황금올리브 BBQ 본점", category: "치킨", rating: 4.9, review_count: 1420, min_order: 18000, delivery_fee: 3000, delivery_time: "25~35분",
    image_url: "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=600&auto=format&fit=crop",
    menus: [
      { id: 1, name: "황금올리브치킨", price: 20000, desc: "BBQ 시그니처 엑스트라 버진 올리브유 바삭 치킨" },
      { id: 2, name: "황금올리브 양념치킨", price: 21500, desc: "매콤달콤 비비큐 특제 양념 소스" },
      { id: 3, name: "자메이카 통다리구이", price: 22500, desc: "저크소스를 발라 깊은 불맛이 가득한 통다리" }
    ]
  },
  {
    name: "엽기떡볶이 역삼점", category: "분식", rating: 4.8, review_count: 980, min_order: 14000, delivery_fee: 2500, delivery_time: "30~40분",
    image_url: "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&auto=format&fit=crop",
    menus: [
      { id: 4, name: "엽기떡볶이(기본)", price: 14000, desc: "치즈, 햄, 쿨피스가 기본 포함된 맛있게 매운맛" },
      { id: 5, name: "로제떡볶이", price: 16000, desc: "부드러운 크림과 엽떡 특제 소스의 중독적인 조화" },
      { id: 6, name: "모둠튀김 (야채/만두/김말이)", price: 3500, desc: "바삭하고 고소한 수제 튀김 모둠 세트" }
    ]
  },
  {
    name: "쉑쉑버거 강남대로점", category: "버거", rating: 4.7, review_count: 2150, min_order: 15000, delivery_fee: 3500, delivery_time: "20~30분",
    image_url: "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&auto=format&fit=crop",
    menus: [
      { id: 7, name: "쉑버거 (싱글)", price: 8400, desc: "비프패티와 토마토, 양상추, 쉑소스의 시그니처 버거" },
      { id: 8, name: "스모크쉑", price: 10600, desc: "애플우드 훈연 베이컨과 매콤한 체리 페퍼" },
      { id: 9, name: "크링클 컷 프라이", price: 4800, desc: "바삭하고 물결 모양의 감자 튀김" }
    ]
  },
  {
    name: "스시로 테헤란로점", category: "일식", rating: 4.9, review_count: 830, min_order: 20000, delivery_fee: 3000, delivery_time: "25~35분",
    image_url: "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600&auto=format&fit=crop",
    menus: [
      { id: 10, name: "특선 모둠초밥 (12p)", price: 18000, desc: "광어, 연어, 참치, 장어, 간장새우 등 엄선 초밥" },
      { id: 11, name: "생연어 초밥 세트 (10p)", price: 17000, desc: "노르웨이산 특등급 신선 생연어 직송" },
      { id: 12, name: "냉모밀 소바", price: 8000, desc: "살얼음 동동 시원하고 깊은 쯔유 국물" }
    ]
  }
];

async function insertSampleStores(client) {
  for (const s of sampleStores) {
    await client.query(`
      INSERT INTO stores (name, category, rating, review_count, min_order, delivery_fee, delivery_time, image_url, menus)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
    `, [s.name, s.category, s.rating, s.review_count, s.min_order, s.delivery_fee, s.delivery_time, s.image_url, JSON.stringify(s.menus)]);
  }
}

async function initDB() {
  let retries = 10;
  while (retries > 0) {
    try {
      const client = await pool.connect();
      console.log(`[${HOSTNAME}] Connected to PostgreSQL store-db successfully.`);

      await client.query(`
        CREATE TABLE IF NOT EXISTS stores (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          category VARCHAR(50) NOT NULL,
          rating NUMERIC(2,1) NOT NULL,
          review_count INT NOT NULL,
          min_order INT NOT NULL,
          delivery_fee INT NOT NULL,
          delivery_time VARCHAR(50) NOT NULL,
          image_url TEXT NOT NULL,
          menus JSONB NOT NULL
        );
      `);

      const res = await client.query('SELECT COUNT(*) FROM stores;');
      if (parseInt(res.rows[0].count) === 0) {
        console.log(`[${HOSTNAME}] Seeding initial store & menu data into PostgreSQL...`);
        await insertSampleStores(client);
      }
      client.release();
      break;
    } catch (err) {
      console.log(`Waiting for PostgreSQL... (${retries} retries left): ${err.message}`);
      retries--;
      await new Promise(r => setTimeout(r, 2000));
    }
  }
}

app.get('/health', async (req, res) => {
  try {
    const dbRes = await pool.query('SELECT 1');
    res.json({
      service: "store-service",
      language: "Node.js 20 (Express)",
      status: "UP",
      hostname: HOSTNAME,
      database: "PostgreSQL 15 (msa-store-db)",
      dbStatus: "CONNECTED",
      port: PORT
    });
  } catch (err) {
    res.status(500).json({
      service: "store-service",
      language: "Node.js 20 (Express)",
      status: "DOWN",
      error: err.message
    });
  }
});

app.all(['/reset', '/store/reset'], async (req, res) => {
  try {
    const client = await pool.connect();
    await client.query('TRUNCATE TABLE stores RESTART IDENTITY;');
    await insertSampleStores(client);
    client.release();
    res.json({ success: true, message: 'Store DB Reset to Initial Seed' });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

app.get('/stores', async (req, res) => {
  try {
    const result = await pool.query('SELECT id, name, category, rating, review_count as "reviewCount", min_order as "minOrder", delivery_fee as "deliveryFee", delivery_fee as "tip", delivery_time as "deliveryTime", image_url as "imageUrl", menus FROM stores ORDER BY id ASC;');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/store/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const result = await pool.query('SELECT id, name, category, rating, review_count as "reviewCount", min_order as "minOrder", delivery_fee as "deliveryFee", delivery_fee as "tip", delivery_time as "deliveryTime", image_url as "imageUrl", menus FROM stores WHERE id = $1;', [id]);
    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Store not found" });
    }
    const row = result.rows[0];
    res.json({
      store: row,
      menus: row.menus
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Store-Service] Node.js 20 listening on port ${PORT}...`);
  initDB();
});
