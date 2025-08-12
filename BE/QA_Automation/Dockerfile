# Stage 1: Build app
FROM eclipse-temurin:21-jdk AS builder

WORKDIR /app
COPY . /app
RUN chmod +x ./gradlew
RUN ./gradlew clean build -x test

# Stage 2: Run app
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
