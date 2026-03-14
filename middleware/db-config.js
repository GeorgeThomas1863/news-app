import dotenv from "dotenv";
dotenv.config({ path: ".env" });

import { MongoClient } from "mongodb";

let db;

export const dbConnect = async () => {
  //connect to mongo server
  const client = await MongoClient.connect(process.env.MONGO_URI);
  db = client.db(process.env.DB_NAME);
};

//create function to call database outside file
export const dbGet = () => {
  //ensure db connection is working
  if (!db) {
    throw { message: "Database connection fucked" };
  }
  return db;
};
