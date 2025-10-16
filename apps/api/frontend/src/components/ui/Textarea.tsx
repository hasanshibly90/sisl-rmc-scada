import React from "react";
export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>){
  return <textarea className={`input ${props.className || ""}`} {...props} />;
}
export default Textarea;
