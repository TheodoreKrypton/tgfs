import dotenv from "dotenv";

export const env = dotenv.config({
  path: `.env.${process.env.NODE_ENV ?? "local"}`,
}).parsed;
