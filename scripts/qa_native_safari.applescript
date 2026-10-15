-- Opens its own temporary Safari window; closes it on success or error.
-- Do not run while another process uses localhost:18779.
set urlList to {"http://127.0.0.1:18779/", "http://127.0.0.1:18779/events/", "http://127.0.0.1:18779/museum/"}
set snippets to {"Хлеб", "Афиша", "Музей"}
set messages to {}
set initialWindows to 0
try
    tell application "Safari"
        set initialWindows to count of windows
        make new document with properties {URL:item 1 of urlList}
        repeat with i from 1 to count of urlList
            set URL of front document to item i of urlList
            delay 1
            set actualURL to URL of front document
            if actualURL does not start with "http://127.0.0.1:18779/" then error "Refusing to examine non-QA page"
            set pageTitle to name of front document
            set pageText to text of front document
            if pageText does not contain item i of snippets then error "Expected page content missing"
            copy ("Safari PASS: " & actualURL & " title=" & pageTitle) to end of messages
        end repeat
        if URL of front document starts with "http://127.0.0.1:18779/" then close front window
        if count of windows is not initialWindows then error "Window count changed"
    end tell
on error errMsg
    tell application "Safari"
        try
            if URL of front document starts with "http://127.0.0.1:18779/" then close front window
        end try
    end tell
    error errMsg
end try
return messages
