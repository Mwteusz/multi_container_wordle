echo Building wordle_container image...
docker build -t wordle_container wordle

echo Building dictionary_container image...
docker build -t dictionary_container dictionary

echo Building mongo_client_container image...
docker build -t mongo_client_container mongodb
