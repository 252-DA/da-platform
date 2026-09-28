# syntax=docker/dockerfile:1
FROM golang:1.26-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go preview.html ./
RUN CGO_ENABLED=0 go build -trimpath -o /out/video-mcp .

FROM python:3.12-slim
ARG YT_DLP_VERSION=2026.8.19
RUN pip install --no-cache-dir "yt-dlp==${YT_DLP_VERSION}" \
    && useradd --create-home --uid 10001 app
COPY --from=build /out/video-mcp /usr/local/bin/video-mcp
USER app
ENV VIDEO_ADDR=0.0.0.0:8002
EXPOSE 8002
CMD ["video-mcp"]
