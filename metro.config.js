// Metro = bundler app HP. Folder Python & data sengaja gak dipindai:
// .venv isinya ribuan file, dan data/trade.db ratusan MB (Expo nganggep .db itu aset).
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
config.resolver.blockList = [
  ...config.resolver.blockList,
  /^(?:\.venv|data|backend|trade|scripts|deploy)$/, // path relatif dari root project
];

module.exports = config;
