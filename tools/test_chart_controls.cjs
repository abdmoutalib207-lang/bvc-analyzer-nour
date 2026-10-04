'use strict';
const assert=require('node:assert/strict');
const {Viewport}=require('../web/chart-controls.js');
const view=new Viewport(1000,200);
assert.deepEqual([view.start,view.end],[800,1000]);
view.pan(-100); assert.deepEqual([view.start,view.end],[700,900]);
view.zoom(.5,.25); assert.deepEqual([view.start,view.end],[725,825]);
view.zoom(2,.25); assert.deepEqual([view.start,view.end],[700,900]);
view.pan(-10000); assert.equal(view.start,0);
view.zoom(10); assert.deepEqual([view.start,view.end],[0,1000]);
view.zoom(.001,1); assert.deepEqual([view.start,view.end],[994,1000]);
view.pan(10000); assert.equal(view.end,1000);
view.set(200,-30); assert.deepEqual([view.start,view.end],[0,200]);
view.set(30,980); assert.deepEqual([view.start,view.end],[970,1000]);
for (const length of [1,3,6,7,21,63,252,1480]) {
  const v=new Viewport(length,252);
  for (let i=0;i<300;i++) {
    if(i%3===0) v.zoom(i%2 ? 1.3 : .75,(i%11)/10);
    else if(i%3===1) v.pan((i%17)-8);
    else v.set((i%67)-15,(i%47)-10);
    assert.ok(Number.isInteger(v.start) && Number.isInteger(v.end));
    assert.ok(v.start>=0 && v.end<=length && v.end-v.start===v.count);
    assert.ok(v.count>=Math.min(6,length));
  }
}
console.log('Chart viewport: anchored zoom, bounds and 2400 short/long-history scenarios passed.');
