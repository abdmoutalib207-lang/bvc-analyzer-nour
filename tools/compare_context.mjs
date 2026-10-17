import fs from 'node:fs';
import assert from 'node:assert/strict';
import {retrieve} from '../backend/context.mjs';
const {index,cases}=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
for(const test of cases)assert.deepEqual(retrieve(index,test.symbols,test.question),test.expected,test.question);
