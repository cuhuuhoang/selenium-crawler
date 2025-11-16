FROM selenium/standalone-chrome:latest

# No extra layers needed; this image exposes the Selenium server on 4444.
EXPOSE 4444 7900
