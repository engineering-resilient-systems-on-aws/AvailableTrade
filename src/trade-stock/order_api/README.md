
building and testing your docker image

first code your flask app locally, then test it out
`order_api.py`

if everything checks out, consider freezing requirements.txt

next build docker images
`docker build -t mypython .`

review the images
`docker images -a`

finally, run your image and test that out
`docker run -d --name trading_api -p 80:80 trading_api:latest`