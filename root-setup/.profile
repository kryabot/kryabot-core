# ~/.profile: executed by Bourne-compatible login shells.

if [ "$BASH" ]; then
  if [ -f ~/.bashrc ]; then
    . ~/.bashrc
  fi
fi

mesg n || true
export PS1="\e[0;31m[\u@\h \W]\$ \e[m "
. ./env.sh