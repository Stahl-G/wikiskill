// Parse model-written JavaScript; never evaluate it. Acorn is vendored alongside.
import fs from 'node:fs';
import {parse} from './acorn.mjs';

function walk(node, visit) {
  if (!node || typeof node !== 'object') return;
  if (typeof node.type === 'string') visit(node);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) for (const child of value) walk(child, visit);
    else if (value && typeof value === 'object') walk(value, visit);
  }
}

function property(node) {
  if (!node.computed && node.property?.type === 'Identifier') return node.property.name;
  if (node.computed && node.property?.type === 'Literal' && typeof node.property.value === 'string') return node.property.value;
  return null;
}

function strings(node) {
  const values = [];
  walk(node, part => {
    if (part.type === 'Literal' && typeof part.value === 'string') values.push(part.value);
    if (part.type === 'TemplateElement') values.push(part.value.cooked ?? part.value.raw);
  });
  return values;
}

function analyze(code) {
  let tree;
  try { tree = parse(code, {ecmaVersion: 'latest', sourceType: 'module', allowAwaitOutsideFunction: true}); }
  catch (error) { return {parse_error: error.message, calls: [], hazards: [], catalog: false}; }
  const aliases = new Set(['tools']), functions = new Map(), declarations = new Set();
  walk(tree, node => {
    if (node.type === 'FunctionDeclaration' && node.id) declarations.add(node.id.name);
    if (node.type === 'VariableDeclarator' && node.id.type === 'Identifier') declarations.add(node.id.name);
  });
  // Common constant aliases, without executing code or interpreting payloads.
  for (let pass = 0; pass < 4; pass++) walk(tree, node => {
    if (node.type !== 'VariableDeclarator' || node.id.type !== 'Identifier') return;
    if (node.init?.type === 'Identifier' && aliases.has(node.init.name)) aliases.add(node.id.name);
    if (node.init?.type === 'MemberExpression' && aliases.has(node.init.object?.name)) {
      const name = property(node.init);
      if (name) functions.set(node.id.name, name);
    }
  });
  const calls = [], hazards = [];
  let catalog = false;
  walk(tree, node => {
    if (node.type === 'Identifier' && node.name === 'ALL_TOOLS') catalog = true;
    if (node.type === 'ImportDeclaration' || node.type === 'ImportExpression') hazards.push('javascript_import');
    if (node.type !== 'CallExpression' && node.type !== 'NewExpression') return;
    const callee = node.callee;
    if (callee.type === 'Identifier') {
      if (functions.has(callee.name)) calls.push({name: functions.get(callee.name), strings: strings(node.arguments)});
      else if (['eval', 'Function', 'fetch', 'require'].includes(callee.name) && !declarations.has(callee.name)) hazards.push('javascript_' + callee.name);
    }
    if (callee.type === 'MemberExpression') {
      if (aliases.has(callee.object?.name)) {
        const name = property(callee);
        if (name) calls.push({name, strings: strings(node.arguments)});
        else hazards.push('dynamic_tool_dispatch');
      }
      let root = callee;
      while (root.type === 'MemberExpression') root = root.object;
      if (root.type === 'Identifier' && ['process', 'Deno', 'Bun', 'globalThis', 'Reflect'].includes(root.name) && !declarations.has(root.name)) hazards.push('javascript_host_access');
    }
  });
  return {parse_error: null, calls, hazards: [...new Set(hazards)], catalog};
}

const input = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(input.map(analyze)));
