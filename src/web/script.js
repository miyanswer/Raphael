// 処理ブロック1: 定数・設定値定義
const STAR_COUNT = 80;
const STAR_MIN_RADIUS = 0.5;
const STAR_MAX_RADIUS = 2.0;
const TWINKLE_SPEED_MIN = 0.005;
const TWINKLE_SPEED_MAX = 0.02;
const CHAR_DELAY_MS = 150;

// 処理ブロック2: Canvas初期化
const canvas = document.getElementById('starCanvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

resizeCanvas();
window.addEventListener('resize', resizeCanvas);

// 処理ブロック3: 星オブジェクト生成
const stars = [];

for (let i = 0; i < STAR_COUNT; i++) {
  stars.push({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    radius: STAR_MIN_RADIUS + Math.random() * (STAR_MAX_RADIUS - STAR_MIN_RADIUS),
    opacity: Math.random(),
    delta: TWINKLE_SPEED_MIN + Math.random() * (TWINKLE_SPEED_MAX - TWINKLE_SPEED_MIN),
    direction: Math.random() < 0.5 ? 1 : -1
  });
}

// 処理ブロック4: 星描画ループ（requestAnimationFrame）
function drawStars() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  stars.forEach(star => {
    star.opacity += star.delta * star.direction;
    if (star.opacity >= 1.0) {
      star.opacity = 1.0;
      star.direction = -1;
    } else if (star.opacity <= 0.0) {
      star.opacity = 0.0;
      star.direction = 1;
    }

    ctx.beginPath();
    ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255, 255, 255, ${star.opacity})`;
    ctx.fill();
  });

  requestAnimationFrame(drawStars);
}

// 処理ブロック5: 文字アニメーション起動
function startTextAnimation() {
  const charElements = document.querySelectorAll('.char');
  charElements.forEach(span => {
    const index = parseInt(span.dataset.char, 10);
    span.style.animationDelay = `${index * CHAR_DELAY_MS}ms`;
    span.classList.add('animate');
  });
}

// 処理ブロック6: エントリーポイント
window.addEventListener('DOMContentLoaded', () => {
  drawStars();
  startTextAnimation();
});
