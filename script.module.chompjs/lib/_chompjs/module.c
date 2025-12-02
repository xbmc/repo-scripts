/*
 * Copyright 2020-2021 Mariusz Obajtek. All rights reserved.
 * License: https://github.com/Nykakin/chompjs/blob/master/LICENSE
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include "parser.h"

static PyObject* parse_python_object(PyObject *self, PyObject *args) {
    const char* string;
    int is_jsonlines = 0;
#if PY_MAJOR_VERSION >= 3
    if (!PyArg_ParseTuple(args, "s|p", &string, &is_jsonlines)) {
#else
    if (!PyArg_ParseTuple(args, "s|i", &string, &is_jsonlines)) {
#endif
        return NULL;
    }

    struct Lexer lexer;
    init_lexer(&lexer, string, is_jsonlines);
    while(lexer.lexer_status == CAN_ADVANCE) {
        advance(&lexer);
    }

    PyObject* ret = Py_BuildValue("s#", lexer.output.data, lexer.output.index-1);
    release_lexer(&lexer);
    if(lexer.lexer_status == ERROR) {
        const char* msg_sting = "Error parsing input near character %d";
        size_t error_buffer_size = snprintf(
            NULL,
            0,
            msg_sting,
            lexer.input_position
        );       
        char* error_buffer = malloc(error_buffer_size + 1);
        sprintf(
            error_buffer,
            msg_sting,
            lexer.input_position - 1
        );
        PyErr_SetString(PyExc_ValueError, error_buffer);
        free(error_buffer);
        return NULL;
    }
    return ret;
}

static PyMethodDef parser_methods[] = { 
    {   
        "parse", parse_python_object, METH_VARARGS,
        "Parse JavaScript object string"
    },  
    {NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef parser_definition = { 
    PyModuleDef_HEAD_INIT,
    "_chompjs",
    "C extension for fast JavaScript object parsing",
    -1, 
    parser_methods
};

PyMODINIT_FUNC PyInit__chompjs(void) {
    Py_Initialize();
    return PyModule_Create(&parser_definition);
}

#else

PyObject* init_chompjs(void) {
    return Py_InitModule("_chompjs", parser_methods);
}

#endif
