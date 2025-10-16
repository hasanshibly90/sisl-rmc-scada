import React from "react";

type Variant = "default" | "primary" | "ghost" | "danger";
type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant };

export default function Button({ variant="default", className="", ...rest }: Props){
  const map:Record<Variant,string> = {
    default:"btn", primary:"btn btn-primary", ghost:"btn btn-ghost", danger:"btn btn-danger"
  };
  return <button className={`${map[variant]} ${className}`} {...rest} />;
}
