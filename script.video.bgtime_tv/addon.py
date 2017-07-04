#!/usr/bin/python
# -*- coding: utf-8 -*-


import gui

def main_menu():
	items = []
	m = gui.List(items)
	m.doModal()
	del m
	return

if __name__ == '__main__':
	main_menu()