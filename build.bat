rem Build wordle_container
echo Building wordle_container image...
docker build -t wordle_container wordle

rem Build dictionary_container
echo Building dictionary_container image...
docker build -t dictionary_container dictionary

rem Build mongo_client_container
echo Building mongo_client_container image...
docker build -t mongo_client_container mongodb
