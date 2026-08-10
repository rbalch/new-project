FROM python:3.13-slim AS dev

ENV PYTHONUNBUFFERED=1
ENV TERM=xterm-256color
ENV COLORTERM=truecolor
ENV DEBIAN_FRONTEND=noninteractive
ENV UV_COMPILE_BYTECODE=1

RUN apt update --yes --quiet && apt install --yes --quiet --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    wget \
	jq \
	rsync \
	tmux \
    git \
    sudo \
    vim \
    zsh \
    locales \
    python3-dev \
    openssh-client \
    procps \
    gnupg \
    lsb-release

# Fix locale (resolves VSCode remote terminal issues)
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

# Node.js 24
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && node -v && npm -v

# Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update && apt-get install -y google-cloud-cli

# uv
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/zsh $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

RUN mkdir -p /app/.venv \
    && chown -R $USERNAME:$USERNAME /app

RUN mkdir -p /home/dev/.vscode-server \
    && mkdir -p /home/dev/history \
    && chown -R $USERNAME:$USERNAME /home/dev/

WORKDIR /app

RUN chown -R $USERNAME:$USERNAME /app
USER $USERNAME

ENV PATH="/app/.venv/bin:$PATH"

# Claude Code CLI — the harness is authored interactively in this container.
# Uses the official native installer (the npm `install` subcommand no longer
# self-bootstraps the platform binary under npx).
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && echo 'export PATH="$HOME/.local/bin:$PATH"' >> ${HOME}/.zshrc

ENV PATH="/home/dev/.local/bin:$PATH"

# oh-my-zsh + plugins
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \
    && git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions ~/.oh-my-zsh/custom/plugins/zsh-autosuggestions \
    && git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting ~/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting

RUN sed -i 's/^plugins=.*/plugins=(git docker node npm zsh-autosuggestions zsh-syntax-highlighting)/' ~/.zshrc

RUN echo 'alias ll="ls -lah"' >> ~/.zshrc \
    && echo 'alias gemini="GOOGLE_CLOUD_PROJECT= npx @google/gemini-cli"' >> ~/.zshrc \
    && echo 'export HISTFILE=$HOME/history/.zsh_history' >> ~/.zshrc
