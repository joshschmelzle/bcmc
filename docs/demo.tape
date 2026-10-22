# Regenerate docs/demo.gif from the repo root with: vhs docs/demo.tape (needs vhs, tmux and an installed .venv)
Output docs/demo.gif
Set Shell "bash"
Set FontSize 14
Set Width 1300
Set Height 760
Set Padding 16
Set Theme "Dracula"
Set TypingSpeed 45ms
Env PS1 "$ "
Env PATH ".venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
Env BASH_SILENCE_DEPRECATION_WARNING "1"
Hide
Type `tmux -f /dev/null new-session -s demo "bash --norc" \; set status off \; set pane-border-status top \; set pane-border-format " #{pane_title} " \; set pane-border-style fg=colour244 \; set pane-active-border-style fg=colour244 \; select-pane -T "client (receive)" \; split-window -v "bash --norc" \; select-pane -T "server (send)" \; select-pane -t 0` Enter
Sleep 2s
Show
Type "bcmc -c -mc" Enter
Sleep 1.2s
Ctrl+B
Type "o"
Sleep 200ms
Type "bcmc -s -mc" Enter
Sleep 6.2s
Ctrl+C
Sleep 600ms
Ctrl+B
Type "o"
Ctrl+C
Sleep 3s
Hide
Type "tmux kill-server" Enter
Sleep 500ms
