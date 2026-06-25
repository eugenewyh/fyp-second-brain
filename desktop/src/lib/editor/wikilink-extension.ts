import { Mark, mergeAttributes, markInputRule } from "@tiptap/core";

export const WikiLink = Mark.create({
  name: "wikiLink",

  addAttributes() {
    return {
      target: {
        default: null,
        parseHTML: (element) => element.getAttribute("data-wikilink"),
      },
      alias: {
        default: null,
        parseHTML: (element) => element.textContent?.trim() ?? null,
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: "a[data-wikilink]",
        getAttrs: (element) => {
          const el = element as HTMLElement;
          const target = el.getAttribute("data-wikilink");
          if (!target) return false;
          const alias = el.textContent?.trim() || target;
          return { target, alias };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    const target = HTMLAttributes.target ?? "";
    return [
      "a",
      mergeAttributes(HTMLAttributes, {
        "data-wikilink": target,
        class: "wikilink",
        href: "#",
      }),
      0,
    ];
  },

  addInputRules() {
    return [
      markInputRule({
        find: /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]$/,
        type: this.type,
        getAttributes: (match) => ({
          target: match[1].trim(),
          alias: (match[2] ?? match[1]).trim(),
        }),
      }),
    ];
  },
});