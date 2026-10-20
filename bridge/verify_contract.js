const fs = require('fs');
const path = require('path');
const https = require('https');

const ENV_FILE = path.resolve(__dirname, '.env.base');
const CONTRACT_ADDRESS = '0x623c84A5E04bF715018203334b0eFE41696eBC3E';
const DEPLOYER_ADDRESS = '0x484eD370DEd0D36e36AAD469a2AFE5D69B1A005D';

function loadEnv() {
  if (fs.existsSync(ENV_FILE)) {
    const content = fs.readFileSync(ENV_FILE, 'utf8');
    content.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        const [k, ...v] = trimmed.split('=');
        if (!process.env[k.trim()]) {
          process.env[k.trim()] = v.join('=').trim();
        }
      }
    });
  }
}

loadEnv();

const sourcePath = path.resolve(__dirname, 'contracts', 'WrappedDOOM.sol');
const sourceCode = fs.readFileSync(sourcePath, 'utf8');
const constructorArgs = '000000000000000000000000' + DEPLOYER_ADDRESS.toLowerCase().replace('0x', '');

const apiKey = process.env.BASESCAN_API_KEY || process.env.ETHERSCAN_API_KEY;

console.log('=============================================================');
console.log('🛡️  WRAPPED DOOM (wDOOM) | BASESCAN VERIFICATION ENGINE');
console.log('=============================================================');
console.log(`Contract:              ${CONTRACT_ADDRESS}`);
console.log(`Compiler Version:      v0.8.20+commit.a1b79de6`);
console.log(`Optimization:          Yes (200 runs)`);
console.log(`Constructor Argument:  ${constructorArgs}`);
console.log(`Basescan Verify URL:   https://basescan.org/verifyContract?a=${CONTRACT_ADDRESS}`);
console.log('-------------------------------------------------------------');

if (!apiKey) {
  console.log('ℹ️  No BASESCAN_API_KEY detected in .env.base.');
  console.log('   You can verify in 30 seconds via the web browser:');
  console.log(`   1. Open: https://basescan.org/verifyContract?a=${CONTRACT_ADDRESS}`);
  console.log('   2. Select:');
  console.log('      - Compiler Type: Solidity (Single file)');
  console.log('      - Compiler Version: v0.8.20+commit.a1b79de6');
  console.log('      - Open Source License: MIT License (MIT)');
  console.log('   3. On the next page:');
  console.log('      - Optimization: Yes (Runs: 200)');
  console.log('      - Paste Solidity code from: bridge/contracts/WrappedDOOM.sol');
  console.log(`      - Constructor Arguments: ${constructorArgs}`);
  console.log('   4. Click "Verify and Publish".');
  console.log('=============================================================\n');
  process.exit(0);
}

console.log('Submitting contract source code to Basescan API...');
const postData = new URLSearchParams({
  apikey: apiKey,
  module: 'contract',
  action: 'verifysourcecode',
  contractaddress: CONTRACT_ADDRESS,
  sourceCode: sourceCode,
  codeformat: 'solidity-single-file',
  contractname: 'WrappedDOOM',
  compilerversion: 'v0.8.20+commit.a1b79de6',
  optimizationUsed: '1',
  runs: '200',
  constructorArguements: constructorArgs,
  evmversion: 'paris',
  licenseType: '3'
}).toString();

const options = {
  hostname: 'api.basescan.org',
  port: 443,
  path: '/api',
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Content-Length': Buffer.byteLength(postData),
    'User-Agent': 'Mozilla/5.0'
  }
};

const req = https.request(options, (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    try {
      const parsed = JSON.parse(data);
      console.log('Response:', parsed);
    } catch (e) {
      console.log('Raw response:', data);
    }
  });
});

req.on('error', (e) => {
  console.error('Request failed:', e.message);
});

req.write(postData);
req.end();
