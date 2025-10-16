import React from "react";

export function Table({className="", ...rest}: React.HTMLAttributes<HTMLTableElement>){
  return <table className={`table ${className}`} {...rest} />;
}
export function THead(props: React.HTMLAttributes<HTMLTableSectionElement>){ return <thead {...props} />; }
export function TBody(props: React.HTMLAttributes<HTMLTableSectionElement>){ return <tbody {...props} />; }
export function TR(props: React.HTMLAttributes<HTMLTableRowElement>){ return <tr {...props} />; }
export function TH(props: React.ThHTMLAttributes<HTMLTableCellElement>){ return <th {...props} />; }
export function TD(props: React.TdHTMLAttributes<HTMLTableCellElement>){ return <td {...props} />; }

export default { Table, THead, TBody, TR, TH, TD };
