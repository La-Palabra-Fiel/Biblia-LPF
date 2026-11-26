import { readFileSync } from "node:fs";

const mappingUrl = new URL("../../../../tools/consumer_books.json", import.meta.url);
const sourceToConsumerBookId = JSON.parse(readFileSync(mappingUrl, "utf8"));

export function consumerBookId(sourceBookId) {
  return sourceToConsumerBookId[sourceBookId] || sourceBookId;
}
