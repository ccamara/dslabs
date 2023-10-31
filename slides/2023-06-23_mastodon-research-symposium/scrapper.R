library(httr)
library(jsonlite)


# FediDB ------------------------------------------------------------------

# FediDB uses a crawler to get info from known servers. The process is somewhat
# documented here: https://fedidb.org/crawler.html
# API Documentation: https://fedidb.org/docs/api/v1

res_software <- GET("https://api.fedidb.org/v1/software?limit=40")
res_servers <- GET("https://api.fedidb.org/v1/servers?limit=40")

df_software <- as.data.frame(fromJSON(rawToChar(res_software$content)))
df_software$date_scraped <- Sys.Date()

df_servers <- as.data.frame(fromJSON(rawToChar(res_servers$content))$data)
df_servers$date_scraped <- Sys.Date()

write.csv(df_software, "slides/2023-06-23_mastodon-research-symposium/data/fedidb_software.csv", row.names = FALSE)
write.csv(df_servers, "slides/2023-06-23_mastodon-research-symposium/data/fedidb_servers.csv", row.names = FALSE)
