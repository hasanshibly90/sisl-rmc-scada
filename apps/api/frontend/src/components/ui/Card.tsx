import React from "react";

type Props = React.HTMLAttributes<HTMLDivElement> & { as?: keyof JSX.IntrinsicElements };
export function Card({ as:Tag="div", className="", ...rest }: Props){
  return <Tag className={`card ${className}`} {...rest} />;
}
export function Panel({ as:Tag="section", className="", ...rest }: Props){
  return <Tag className={`panel ${className}`} {...rest} />;
}
export default Card;
