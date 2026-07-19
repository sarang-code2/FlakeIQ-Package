#!/usr/bin/env node

const { isVenvReady } = require('../lib/config');
const { setup } = require('../lib/setup');

console.log('');
console.log('  FlakeIQ — setting up Python environment...');

if (isVenvReady()) {
  console.log('  Python environment already ready.');
} else {
  const ok = setup();
  if (!ok) {
    console.log('');
    console.log('  Setup incomplete. FlakeIQ reporter will work, but');
    console.log('  dashboard/classifier need Python 3.11+ installed.');
  }
}

console.log('');
console.log('  Next steps:');
console.log('    Add to playwright.config.ts:');
console.log("      reporter: [['flakeiq/reporter']]");
console.log('');
console.log('    Start dashboard:');
console.log('      npx flakeiq serve');
console.log('');
