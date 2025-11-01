import { Table } from "@mui/joy";
import { BomEntry } from "../../openapi/inventory";

interface BomEntryTableProps {
  entries: BomEntry[];
}

export default function BomEntryTable({ entries }: BomEntryTableProps) {
  if (entries.length === 0) {
    return <div>No entries</div>;
  }

  return (
    <Table>
      <thead>
        <tr>
          <th>Qty</th>
          <th>Device</th>
          <th>Value</th>
          <th>Description</th>
          <th>Manufacturer</th>
          <th>Parts</th>
          <th>Comments</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, idx) => (
          <tr key={idx}>
            <td>{entry.qty}</td>
            <td>{entry.device}</td>
            <td>{entry.value}</td>
            <td>{entry.description}</td>
            <td>{entry.manufacturer}</td>
            <td>{entry.parts?.join(', ')}</td>
            <td>{entry.comments}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

