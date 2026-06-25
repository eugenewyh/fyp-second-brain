import { Mark, mergeAttributes } from "@tiptap/core";
import { markInputRule } from "@tiptap/core";

export const WikiLink = Mark.create({
  name: "wikiLink",

  addAttributes() {
    return {
      target: { default: null },
      alias: { default: null },
    };
  },

  parseHTML() {
    return [{ tag: "a[data-wikilink]" }];
  },

  renderHTML({ HTMLAttributes }) {
    const target = HTMLAttributes.target ?? "";
    const alias = HTMLAttributes.alias ?? target;
    return [
      "a",
      mergeAttributes(HTMLAttributes, {
        "data-wikilink": target,
        class: "wikilink",
        href: "#",
      }),
      alias,
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