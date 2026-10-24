import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/employer-logo-display.js', import.meta.url), 'utf8');
const SIDE = 64;

function fixture({ color = [33, 91, 163, 255], rect = [18, 18, 45, 45], opaqueWhite = false, width = 384, height = 384, src = 'https://hdcareers.in/assets/company-owner/sample.png' } = {}) {
  const pixels = new Uint8ClampedArray(SIDE * SIDE * 4);
  for (let y = 0; y < SIDE; y++) for (let x = 0; x < SIDE; x++) {
    const k = (y * SIDE + x) * 4;
    const visible = x >= rect[0] && x <= rect[2] && y >= rect[1] && y <= rect[3];
    const rgba = visible ? color : opaqueWhite ? [255, 255, 255, 255] : [0, 0, 0, 0];
    pixels.set(rgba, k);
  }
  const classes = new Set();
  const host = {
    classList: {
      add: (value) => classes.add(value),
      remove: (value) => classes.delete(value),
      contains: (value) => classes.has(value)
    }
  };
  const canvas = { getContext: () => ({ drawImage() {}, getImageData: () => ({ data: pixels }) }) };
  const document = {
    readyState: 'loading',
    addEventListener() {},
    querySelectorAll: () => [],
    createElement: (tag) => tag === 'canvas' ? canvas : { style: {}, textContent: '', className: '' }
  };
  const window = {};
  const img = {
    alt: 'Sample logo',
    dataset: { mark: 'SM', color: '#0969da' },
    naturalWidth: width, naturalHeight: height,
    complete: true, src,
    style: { transform: '' },
    closest: () => host,
    replaceWith: (node) => { host.replacement = node; }
  };
  vm.runInNewContext(source, { window, document, location: { href: 'https://hdcareers.in/', origin: 'https://hdcareers.in' }, URL });
  window.hdEnhanceLogo(img);
  return { host, img, classes, adapt: window.hdEnhanceLogo };
}

test('white transparent logo gets a navy backdrop', () => {
  const { host, img, classes } = fixture({ color: [250, 250, 250, 255] });
  assert.equal(classes.has('hd-logo-dark'), true);
  assert.equal(host.replacement, undefined);
  assert.ok(img.style.transform.startsWith('scale('));
});

test('small compact colored mark becomes larger without a dark box', () => {
  const { host, img, classes } = fixture({ rect: [25, 25, 38, 38] });
  assert.equal(classes.has('hd-logo-dark'), false);
  assert.equal(host.replacement, undefined);
  assert.ok(Number(img.style.transform.match(/scale\(([\d.]+)\)/)?.[1]) > 1.3);
});

test('long wordmarks are replaced with the employer initials', () => {
  const { host, classes } = fixture({ rect: [4, 26, 59, 36] });
  assert.equal(host.replacement?.textContent, 'SM');
  assert.equal(host.replacement?.className, 'hd-logo-initials');
  assert.equal(classes.has('hd-logo-dark'), false);
});

test('naturally wide remote image falls back without canvas sampling', () => {
  const { host } = fixture({ width: 650, height: 100 });
  assert.equal(host.replacement?.textContent, 'SM');
});

test('opaque white background with colored emblem stays light', () => {
  const { host, classes } = fixture({ opaqueWhite: true });
  assert.equal(classes.has('hd-logo-dark'), false);
  assert.equal(host.replacement, undefined);
});

test('PhonePe and all existing cached icons retain their original presentation', () => {
  const { host, classes, img } = fixture({
    src: 'https://hdcareers.in/assets/company-icons/phonepe-1590c80-28a3879cec.svg',
    width: 900, height: 100, color: [255, 255, 255, 255]
  });
  assert.equal(host.replacement, undefined, 'Never turn PhonePe logo into initials');
  assert.equal(classes.has('hd-logo-dark'), false, 'Keep the old background');
  assert.equal(img.dataset.hdLogoChecked, undefined, 'Do not apply auto fit');
  assert.equal(img.style.transform, '', 'Do not overwrite zoom');
});
