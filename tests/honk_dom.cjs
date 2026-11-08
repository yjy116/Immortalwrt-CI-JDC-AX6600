// Minimal browser I/O for executing upstream LuCI view and switch code in Node.
function createDom() {
  const nodes = [];
  function element(tag, attrs = {}, children = []) {
    const classes = new Set((attrs.class || '').split(' ').filter(Boolean));
    const node = { tag, ...attrs, children, value: '', events: {}, style: {},
      classList: {
        add(name) { classes.add(name); },
        toggle(name, force) { if (force) classes.add(name); else classes.delete(name); },
        contains(name) { return classes.has(name); }
      },
      appendChild(child) { this.children = [...this.children, child]; },
      addEventListener(event, callback) { this.events[event] = callback; },
      dispatchEvent(event) { this.events[event.type]?.(event); },
      setAttribute(name, value) { this[name] = value; },
      removeAttribute(name) { delete this[name]; },
      querySelector(selector) {
        const tags = selector.split(',').map(tag => tag.trim());
        return Array.isArray(this.children) && this.children.find(child => tags.includes(child.tag));
      }
    };
    nodes.push(node);
    return node;
  }
  const document = { head: element('head'), createElement: element,
    createTextNode: text => text, getElementById: id => nodes.find(node => node.id === id) };
  return { nodes, element, document };
}

module.exports = { createDom };
