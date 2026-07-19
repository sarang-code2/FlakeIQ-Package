const fs = require('fs');

class FlakeReporter {
  constructor(options) {
    this.stepsMap = new Map();
    this.outputFile = (options && options.outputFile) || 'flake-results.jsonl';
    this.sessionId = 'run_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  }

  onStepBegin(test, result, step) {
    if (step.category !== 'pw:api') return;
    const key = test.id + '::' + result.retry;
    if (!this.stepsMap.has(key)) this.stepsMap.set(key, []);
    const steps = this.stepsMap.get(key);
    steps.push(step.title);
    if (steps.length > 10) steps.shift();
  }

  onTestEnd(test, result) {
    const key = test.id + '::' + result.retry;
    const lastActions = this.stepsMap.get(key) || [];
    this.stepsMap.delete(key);

    const findAnnotation = (type) => {
      const a = result.annotations.find(x => x.type === type);
      return a ? a.description : '';
    };
    const platform = findAnnotation('device.platform');
    const deviceId = findAnnotation('device.id');

    const record = {
      test_file: test.location.file,
      test_name: test.title,
      platform,
      device_id: deviceId,
      duration_ms: result.duration,
      result: result.status,
      error_message: result.error ? result.error.message || '' : '',
      last_actions: lastActions,
      classification: null,
      classification_reason: null,
      screen_name: guessScreen(test.title, lastActions),
      session_id: this.sessionId,
      run_at: new Date().toISOString(),
    };

    fs.appendFileSync(this.outputFile, JSON.stringify(record) + '\n');
  }
}

const SCREEN_MAP = {
  alert: ['alerts', 'alert', 'dialog', 'modal'],
  animation: ['animation', 'animate', 'transition'],
  calendar: ['calendar', 'date', 'picker'],
  form: ['formcontrols', 'form', 'input', 'textfield'],
  gesture: ['gestures', 'gesture', 'swipe', 'pinch', 'pan'],
  list: ['lists', 'list', 'scroll', 'flatlist'],
  login: ['login', 'register', 'signin', 'auth', 'validation'],
  media: ['media', 'image', 'video', 'photo'],
  profile: ['profile', 'edit', 'save', 'logout', 'toggle'],
  signature: ['signature', 'draw', 'canvas'],
  home: ['home', 'landing', 'main'],
};

function guessScreen(testName, actions) {
  // Pattern: "ScreenName - action description" or "screen name - action"
  const dashIdx = testName.indexOf(' - ');
  if (dashIdx !== -1) {
    const prefix = testName.slice(0, dashIdx).trim().toLowerCase();
    for (const [screen, aliases] of Object.entries(SCREEN_MAP)) {
      if (aliases.some(a => prefix === a || prefix.startsWith(a))) return screen;
    }
    // If prefix is a simple word, return it directly (e.g. "Alerts" -> "alerts")
    if (/^[a-z]+$/.test(prefix)) return prefix;
  }

  // Fallback: keyword match in full test name
  const lower = testName.toLowerCase();
  for (const [screen, keywords] of Object.entries(SCREEN_MAP)) {
    if (keywords.some(k => lower.includes(k))) return screen;
  }

  // Last resort: check actions
  for (const action of actions) {
    const lowerAction = action.toLowerCase();
    for (const [screen, keywords] of Object.entries(SCREEN_MAP)) {
      if (keywords.some(k => lowerAction.includes(k))) return screen;
    }
  }
  return 'unknown';
}

module.exports = FlakeReporter;
