const fs = require('fs');

class FlakeReporter {
  constructor(options) {
    this.stepsMap = new Map();
    this.outputFile = (options && options.outputFile) || 'flake-results.jsonl';
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
      session_id: deviceId,
      run_at: new Date().toISOString(),
    };

    fs.appendFileSync(this.outputFile, JSON.stringify(record) + '\n');
  }
}

function guessScreen(testName, actions) {
  const navMatch = testName.match(/nav(\w+)/i);
  if (navMatch) return navMatch[1].toLowerCase();
  const screenKeywords = {
    login: ['login', 'signin', 'auth'],
    profile: ['profile', 'edit', 'save'],
    form: ['form', 'input', 'text', 'type'],
    list: ['list', 'scroll', 'flatlist'],
    alert: ['alert', 'dialog', 'modal'],
    animation: ['animation', 'animate', 'transition'],
    calendar: ['calendar', 'date', 'picker'],
    gesture: ['gesture', 'swipe', 'pinch', 'pan'],
    media: ['media', 'image', 'video', 'photo'],
    signature: ['signature', 'draw', 'canvas'],
    home: ['home', 'landing', 'main'],
  };
  const lower = testName.toLowerCase();
  for (const [screen, keywords] of Object.entries(screenKeywords)) {
    if (keywords.some(k => lower.includes(k))) return screen;
  }
  for (const action of actions) {
    const lowerAction = action.toLowerCase();
    for (const [screen, keywords] of Object.entries(screenKeywords)) {
      if (keywords.some(k => lowerAction.includes(k))) return screen;
    }
  }
  return 'unknown';
}

module.exports = FlakeReporter;
