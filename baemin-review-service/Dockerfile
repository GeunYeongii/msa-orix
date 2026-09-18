FROM ruby:3.2-alpine
RUN apk add --no-cache build-base
WORKDIR /app
COPY Gemfile* ./
RUN bundle install
COPY . .
EXPOSE 8085
CMD ["bundle", "exec", "ruby", "app.rb"]
