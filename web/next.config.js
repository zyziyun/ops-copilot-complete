/** @type {import('next').NextConfig} */
const nextConfig = {
  // emit a self-contained server bundle for a slim Docker image
  output: "standalone",
};
module.exports = nextConfig;
