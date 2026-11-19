import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";

function remarkHtmlBreaks() {
  return (tree) => {
    const visit = (node) => {
      if (!Array.isArray(node.children)) return;

      node.children = node.children.flatMap((child) => {
        if (
          child.type === "html" &&
          /^(?:<br\s*\/?>(\s*))*$/i.test(child.value.trim())
        ) {
          const breakCount = (child.value.match(/<br\s*\/?>/gi) || []).length;
          return Array.from({ length: breakCount }, () => ({ type: "break" }));
        }

        visit(child);
        return [child];
      });
    };

    visit(tree);
  };
}

export default function AssistantMessage({ content }) {
  return (
    <div className="assistant-markdown">
      <ReactMarkdown remarkPlugins={[remarkBreaks, remarkHtmlBreaks]}>
        {typeof content === "string" ? content : ""}
      </ReactMarkdown>
    </div>
  );
}
