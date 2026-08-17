const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('js/commands.js', 'utf8');
const context = { window: {} };
vm.createContext(context);
vm.runInContext(source, context);
const list = context.window.COMMAND_LIST;
const counts = list.reduce((acc, command) => {
  acc[command.type] = (acc[command.type] || 0) + 1;
  return acc;
}, {});
const invalid = list.filter(command => !['slash', 'text'].includes(command.type));
console.log(JSON.stringify({ total: list.length, counts, invalid }, null, 2));
if (invalid.length) process.exit(1);
