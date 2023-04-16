/*
 * Copyright 2020-2021 Mariusz Obajtek. All rights reserved.
 * License: https://github.com/Nykakin/chompjs/blob/master/LICENSE
 */

#ifndef CHOMPJS_PARSER_H
#define CHOMPJS_PARSER_H

#include <stddef.h>
#include <stdbool.h>

#include "buffer.h"

struct Lexer;

/**
    States of internal state machine:
    * begin - start parsing
    * json - handle special characters: "[", "{", "}", "]", ",", ":"
    * value - handle a JSON value, such as strings and numbers
    * end - finish work
    * error - finish work, mark an error
*/
struct State* begin(struct Lexer* lexer);
struct State* json(struct Lexer* lexer);
struct State* value(struct Lexer* lexer);
struct State* end(struct Lexer* lexer);
struct State* error(struct Lexer* lexer);

/*
    Helper functions used in "value" state
    * handle_quoted - handles quoted strings
    * handle_numeric - handle numbers
    * handle_unrecognized - save all unrecognized data as a string
*/
struct State* handle_quoted(struct Lexer* lexer);
struct State* handle_numeric(struct Lexer* lexer);
struct State* handle_unrecognized(struct Lexer* lexer);

/**
    State wrapper
*/
struct State {
    struct State* (*change)(struct Lexer *);
};

/** Possible results of internal state machine state change state */
typedef enum {
    CAN_ADVANCE,
    FINISHED,
    ERROR,
} LexerStatus;

/** Main object, responsible for everything */
struct Lexer {
    const char* input;
    size_t output_size;
    struct CharBuffer output;
    size_t input_position;
    size_t output_position;
    LexerStatus lexer_status;
    struct State* state;
    struct CharBuffer nesting_depth;
    size_t unrecognized_nesting_depth;
    bool is_jsonlines;
    bool is_key;
};

/** Switch state of internal state machine */
void advance(struct Lexer* lexer);

/** Get next char, ignore whitespaces */
char next_char(struct Lexer* lexer);

/** Get previously handled char */
char last_char(struct Lexer* lexer);

/** Send character to output buffer, advance input position */
void emit(char c, struct Lexer* lexer);

/** Send character to output buffer, keep old input position */
void emit_in_place(char c, struct Lexer* lexer);

/** Remove last character from output buffer */
void unemit(struct Lexer* lexer);

/** Send string to output buffer, advance input position */
void emit_string(const char *s, size_t size, struct Lexer* lexer);

/** Send string to output buffer, keep old input position */
void emit_string_in_place(const char *s, size_t size, struct Lexer* lexer);

/** Handle comments in JSON body */
void handle_comments(struct Lexer* lexer);

/** Initialize main lexer object*/
void init_lexer(struct Lexer* lexer, const char* string, bool is_jsonlines);

/** Release main lexer object and its memory */
void release_lexer(struct Lexer* lexer);

#endif
