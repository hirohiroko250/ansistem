/**
 * PWA アイコン生成スクリプト
 *
 * 使用方法:
 * 1. npm install sharp
 * 2. node scripts/generate-icons.js
 */

const fs = require('fs');
const path = require('path');

// SVGアイコンのテンプレート
const generateSVG = (size) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2563eb"/>
      <stop offset="100%" style="stop-color:#1d4ed8"/>
    </linearGradient>
  </defs>
  <rect width="${size}" height="${size}" rx="${Math.round(size * 0.1875)}" fill="url(#bg)"/>
  <text x="${size/2}" y="${size * 0.625}" font-family="Arial, sans-serif" font-size="${size * 0.39}" font-weight="bold" fill="white" text-anchor="middle">O</text>
  <circle cx="${size/2}" cy="${size * 0.273}" r="${size * 0.078}" fill="white" opacity="0.9"/>
</svg>`;

const iconSizes = [72, 96, 128, 144, 152, 167, 180, 192, 384, 512];
const iconsDir = path.join(__dirname, '../public/icons');

async function generateIcons() {
  try {
    const sharp = require('sharp');

    // アイコンディレクトリがなければ作成
    if (!fs.existsSync(iconsDir)) {
      fs.mkdirSync(iconsDir, { recursive: true });
    }

    for (const size of iconSizes) {
      const svg = generateSVG(size);
      const outputPath = path.join(iconsDir, `icon-${size}x${size}.png`);

      await sharp(Buffer.from(svg))
        .png()
        .toFile(outputPath);

      console.log(`Generated: icon-${size}x${size}.png`);
    }

    console.log('\\nAll icons generated successfully!');
  } catch (error) {
    if (error.code === 'MODULE_NOT_FOUND') {
      console.log('sharp is not installed. Installing...');
      console.log('Run: npm install sharp');
      console.log('Then: node scripts/generate-icons.js');

      // sharpなしでSVGファイルだけ作成
      console.log('\\nGenerating SVG files instead...');
      for (const size of iconSizes) {
        const svg = generateSVG(size);
        const outputPath = path.join(iconsDir, `icon-${size}x${size}.svg`);
        fs.writeFileSync(outputPath, svg);
        console.log(`Generated SVG: icon-${size}x${size}.svg`);
      }
    } else {
      throw error;
    }
  }
}

generateIcons();
