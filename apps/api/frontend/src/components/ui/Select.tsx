import React from "react";
export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>){
  return <select className={`select ${props.className || ""}`} {...props} />;
}
export default Select;
