#!/usr/bin/python
# coding=utf-8

# Create by 
# Francisco Garcia de la Corte (Pacoard)
# Eduardo Merino Machuca (Merinom)

###############################################################
# Para que el script funcione, debe tener en la misma carpeta #
# los archivos image.qcow2 y template.xml                     #
###############################################################

#obtenemos argumentos de la linea de comandos, en array sys.argv
import sys
import os

from lxml import etree #importamos libreria para trabajar con xml
from copy import deepcopy #para copiar etiquetas

import glob #para contar n de archivos en la carpeta https://docs.python.org/2/library/glob.html
import subprocess #importamos subprocesos


#funcion para crear maquinas (imagen y xml)
def crearMaquina (id):	
	#crear la maquina
	os.system("qemu-img create -f qcow2 -b image.qcow2 cdps-vm_"+id+".qcow2")
	
	#ARCHIVOS DE CONFIGURACION https://docs.python.org/2/library/xml.etree.elementtree.html
	
	#obtener info de la plantilla
	xml = etree.parse("template.xml")
	root = xml.getroot()
	
	#modificar etiquetas
	nombre = root.find("name")
	nombre.text = id
	
	#ruta de la imagen
	source = root.find("devices").find("disk").find("source")
	currentDirectory = os.getcwd() #adaptativo a donde se encuentre este script
	source.set("file", currentDirectory+"/cdps-vm_"+id+".qcow2")
	
	#interfaces de conexion
	sourceBridge = root.find("devices").find("interface").find("source")
	if (id == "c1"):
		sourceBridge.set("bridge","LAN1")
	elif (id == "lb"):
		#duplicar la etiqueta interface
		devices = root.find("devices")
		devices.append(deepcopy(devices.find("interface")))
		
		i=0
		for interface in devices.iter("interface"):
			if (i==0): #primera interface
				interface.find("source").set("bridge", "LAN1")
			else: #segunda interface
				interface.find("source").set("bridge", "LAN2")
			i+=1
	else: #si es s1...s5
		sourceBridge.set("bridge","LAN2")
	#crear y guardar en un xml nuevo
	xml.write(id+".xml")

#PARTE OPCIONAL: configuracion de hostname y red de las vm's. Necesita de una carpeta vacia "mnt"

def configuracionOpcional(id):
	os.system("mkdir mnt")
	os.system("sudo vnx_mount_rootfs -s -r cdps-vm_"+id+".qcow2 mnt") #montar sistema de ficheros en mnt
	#modificacion de hostname
	os.system("echo "+id+" > mnt/etc/hostname")
	#Para que, al acceder a la IP desde el host, se vea un index.html con el nombre de la maquina
	os.system("echo "+id+" > mnt/var/www/html/index.html")
	#IP distinta dependiendo de la VM, en mnt/etc/hosts
	line_to_append = ""
	value_for_rcLocal = "" #comandos para ejecutar al iniciar cada maquina
	
	comandoALanzar = "xr --verbose --server tcp:0:80 "
	for x in range(1,int(sys.argv[3])+1):
		comandoALanzar = comandoALanzar + "--backend 10.0.2.1"+str(x)+":80"
	comandoALanzar = comandoALanzar + " --web-interface 0:8001"

	if (id == "c1"):
		print (id + "=====================================================================")
		line_to_append = "10.0.1.2	c1\n"
		value_for_rcLocal = """sudo -s <<EOF
ifconfig eth0 10.0.1.2/24
ip route add default via 10.0.1.1
EOF
exit 0""" #default es la interfaz al lado del lb
		
	elif (id == "lb"):
		print (id + "=====================================================================")
		line_to_append = "10.0.1.1	lb\n10.0.2.10	lb"
		value_for_rcLocal = """sudo -s <<EOF
ifconfig eth0 10.0.1.1/24
ifconfig eth1 10.0.2.1/24
echo 1 > /proc/sys/net/ipv4/ip_forward
service apache2 stop"""+comandoALanzar+"""
EOF
exit 0"""
	else: #si es s1...s5, tendra ip 10.0.2.11, 12, 13...
		print (id + "=====================================================================")
		line_to_append = "10.0.2.1"+id[1]+"	"+id+"\n"
		value_for_rcLocal = """sudo -s <<EOF
echo """+id+""" > /var/www/html/index.html
ifconfig eth0 10.0.2.1"""+id[1]+"""/24
ip route add default via 10.0.2.1
EOF
exit 0""" #default es la interfaz al lado del lb
	#modificacion de etc/hosts
	etc_hosts = open("mnt/etc/hosts", "r+")
	etc_hosts_modificado = open("mnt/etc/aux", "w")
	etc_hosts_modificado.write(line_to_append)
	for line in etc_hosts.readlines():
		etc_hosts_modificado.write(line)
	etc_hosts.close()
	os.remove("mnt/etc/hosts")
	etc_hosts_modificado.close()
	os.rename("mnt/etc/aux", "mnt/etc/hosts")
	
	rc_local = open("mnt/etc/init.d/rc.local","a")
	rc_local.write(value_for_rcLocal)
	rc_local.close()

	print("antes de desmontar")	
	os.system("sudo vnx_mount_rootfs -u mnt") #desmontar sistema de ficheros
	print("despues de desmontar")
		

print(sys.argv)

if len(sys.argv) < 2:
	print("pocos argumentos")
	sys.exit()

######################################################
if sys.argv[1] == "create":
	print("create")
	if len(sys.argv) < 3:
		print("Escribir \"-n\"(manual),\"-f\" (desde fichero) para especificar numero de maquinas virtuales")
		sys.exit()
	elif  sys.argv[2] == "-n" :
		if len(sys.argv) < 4:
			print("Falta numero de maquinas a iniciar: 1 a 5")
			sys.exit()
		if(len(glob.glob("aux.txt")) != 0):
			for x in range(1,6):
				if(os.system("grep s"+str(x)+" aux.txt > var.txt")==0):
					os.system("sudo virsh destroy s"+str(x))
			if(os.system("grep lb aux.txt > var.txt")==0):
				os.system("sudo virsh destroy lb")
			if(os.system("grep c1 aux.txt > var.txt")==0):
				os.system("sudo virsh destroy c1")
		if (0 < int(sys.argv[3]) < 6):
			#os.system("echo haciendo")
			for x in range(1,int(sys.argv[3])+1):
				#crear las maquinas aqui
				crearMaquina("s"+str(x))
				configuracionOpcional("s"+str(x))
			#configurar el lb y el c1
			crearMaquina("lb")
			configuracionOpcional("lb")
			crearMaquina("c1")
			configuracionOpcional("c1")
			#configurar bridges y LAN
			if(len(glob.glob("aux.txt")) == 0):
				os.system("sudo brctl addbr LAN1")
				os.system("sudo brctl addbr LAN2")
				os.system("sudo ifconfig LAN1 up")
				os.system("sudo ifconfig LAN2 up")
			os.system("touch aux.txt")
		else:
			print("Numero incorrecto")
	elif sys.argv[2] == "-f":
		if len(sys.argv) < 4:
			print("Falta fichero")
			sys.exit()
		if(len(glob.glob(sys.argv[3])) == 0):
			print("El fichero aportado no existe")
			sys.exit()
		nMaq = open(sys.argv[3], 'r').read()
		nMV = [int(s) for s in nMaq.split() if s.isdigit()]
		nMaq.close()
		if(len(glob.glob("aux.txt")) != 0):
			for x in range(1,6):
				if(os.system("grep s"+str(x)+" aux.txt")!=0):
					os.system("sudo virsh destroy s"+str(x))
			if(os.system("grep lb aux.txt")!=0):
				os.system("sudo virsh destroy lb")
			if(os.system("grep c1 aux.txt")!=0):
				os.system("sudo virsh destroy c1")
		for x in range(1,nMV[0]+1):
			#crear las maquinas aqui
			crearMaquina("s"+str(x))
			configuracionOpcional("s"+str(x))
		#configurar el lb y el c1
		crearMaquina("lb")
		configuracionOpcional("lb")
		crearMaquina("c1")
		configuracionOpcional("c1")
		#configurar bridges y LAN
		#if(len(glob.glob("aux.txt")) == 0):
		os.system("sudo ifconfig LAN1 10.0.1.3/24")
		os.system("sudo ip route add 10.0.0.0/16 via 10.0.1.1")
		os.system("sudo brctl addbr LAN1")
		os.system("sudo brctl addbr LAN2")
		os.system("sudo ifconfig LAN1 up")
		os.system("sudo ifconfig LAN2 up")
		os.system("touch aux.txt")
	else:
		print("Escribir \"-n\" , \"-f\"para especificar numero de maquinas virtuales")
		sys.exit()
	#Configurar conexion del host a las demas maquinas
	os.system("sudo ifconfig LAN1 10.0.1.3/24")
	os.system("sudo ip route add 10.0.0.0/16 via 10.0.1.1")
	os.system("sudo brctl addbr LAN1")
	os.system("sudo brctl addbr LAN2")
	os.system("sudo ifconfig LAN1 up")
	os.system("sudo ifconfig LAN2 up")
#####################################################

elif sys.argv[1] == "start":
	comprobarEntorno = len(glob.glob("aux.txt"))
	if comprobarEntorno == 0:
		print("No se ha creado el entorno")
		sys.exit()
	print("start")
	numeroMaquinas = len(glob.glob("cdps-vm_s*"))
	if numeroMaquinas == 0:
		print("no hay imagenes para arrancar")
		sys.exit()
	if (len(sys.argv) < 3) or ((sys.argv[2] != "-t") and (sys.argv[2] != "-g")):
		print("Especificar tipo de consolas: -t : textual, -g: grafica ")
		sys.exit()
	os.system("sudo virsh list > aux.txt")
	for x in range(1,numeroMaquinas+1):
		if(os.system("grep s"+str(x)+" aux.txt")==0):
			print(str(x) + "ya iniciado")
		else:
			os.system("sudo virsh create s"+str(x)+".xml")
	if(os.system("grep lb aux.txt")==0):
		print("bl ya iniciado")
	else:
		os.system("sudo virsh create lb.xml")
	if(os.system("grep c1 aux.txt")==0):
		print("c1 ya iniciado")
	else:
		os.system("sudo virsh create c1.xml")
	os.system("sudo virsh list > aux.txt")
	#Comprobamos que se hayan iniciado todas las maquinas virtuales, sino, repetimos el start.
	for x in range(1,numeroMaquinas+1):
		salida = os.system("grep s"+str(x)+" aux.txt > var.txt")
		if salida != 0:
			os.system("python x.py start " + sys.argv[2])
			sys.exit()
	salida2 = os.system("grep lb aux.txt > var.txt")
	if salida2 != 0:
		os.system("python x.py start " + sys.argv[2])
		sys.exit()
	salida3 = os.system("grep c1 aux.txt > var.txt")
	if salida3 != 0:
		os.system("python x.py start " + sys.argv[2])
		sys.exit()
	if (sys.argv[2] == "-g"):
		for x in range(1,numeroMaquinas+1): 
			os.system("sudo virt-viewer s"+str(x)+" &")
		os.system("sudo virt-viewer lb &")
		os.system("sudo virt-viewer c1 &")

	elif (sys.argv[2] == "-t"):
		for x in range(1,numeroMaquinas+1): 
			os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 's"+str(x)+"' -e 'sudo virsh console s"+str(x)+"'&")
		os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 'lb' -e 'sudo virsh console lb'&")
		os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 'c1' -e 'sudo virsh console c1'&")

#######################################################

elif sys.argv[1] == "stop":
	comprobarEntorno= len(glob.glob("aux.txt"))
	if comprobarEntorno == 0:
		print("No se ha creado el entorno")
		sys.exit()
	salida = os.system("grep s1 aux.txt > var.txt")
	if salida != 0:
		print("No hay maquinas virtuales en funcionamiento")
		sys.exit()
	if(len(sys.argv) > 2):
		if sys.argv[2] != "-f":
			print("-f para forzar")
			sys.exit()
		if sys.argv[2] == "-f":
			print("Parando maquinas virtuales de forma abrupta")
			salida = os.system("grep s1 aux.txt > var.txt")
			if salida != 0:
				print("No hay maquinas virtuales que parar")
				sys.exit()
			numeroMaquinas = len(glob.glob("cdps-vm_s*"))
			for x in range(1,numeroMaquinas+1): 
				os.system("sudo virsh destroy s"+str(x))
			os.system("sudo virsh destroy lb")
			os.system("sudo virsh destroy c1")
			os.system("sudo virsh list > aux.txt")
		else:
			print("Parametro no valido, -f para forzar stop")
	else:
		print("stop")
		salida = os.system("grep s1 aux.txt > var.txt")
		if salida != 0:
			print("No hay maquinas virtuales que parar")
			sys.exit()
		numeroMaquinas = len(glob.glob("cdps-vm_s*"))
		for x in range(1,numeroMaquinas+1): 
			os.system("sudo virsh shutdown s"+str(x))
		os.system("sudo virsh shutdown lb")
		os.system("sudo virsh shutdown c1")
		os.system("sudo virsh list > aux.txt")
#######################################################


elif sys.argv[1] == "destroy":
	comprobarEntorno= len(glob.glob("aux.txt"))
	if comprobarEntorno == 0:
		print("No se ha creado el entorno")
		sys.exit()
	print("destroy")
	numeroMaquinas = len(glob.glob("cdps-vm_s*"))
	if numeroMaquinas == 0:
		print("No se ha iniciado la creacion de maquinas virtuales que destruir")
		sys.exit()
	for x in range(1,numeroMaquinas+1):
		os.system("rm -f cdps-vm_s"+str(x)+".qcow2")
		os.system("rm -f s"+str(x)+".xml")
	os.system("rm -f cdps-vm_lb.qcow2")
	os.system("rm -f lb.xml")
	os.system("rm -f cdps-vm_c1.qcow2")
	os.system("rm -f c1.xml")
	os.system("sudo ifconfig LAN1 down")
	os.system("sudo ifconfig LAN2 down")
	os.system("sudo brctl delbr LAN1")
	os.system("sudo brctl delbr LAN2")
	os.system("sudo virsh list > aux.txt")
	salida = os.system("grep s1 aux.txt > var.txt")
	if salida != 0:
		print("No hay maquinas virtuales en funcionamiento, solo se han eliminado los ficheros")
		os.system("rm -f aux.txt")
		sys.exit()
	for x in range(1,numeroMaquinas+1):
		os.system("sudo virsh destroy s"+str(x))
	os.system("sudo virsh destroy lb")
	os.system("sudo virsh destroy c1")
	os.system("rm -f aux.txt")
#######################################################
elif sys.argv[1] == "monitor":
	comprobarEntorno= len(glob.glob("aux.txt"))
	if comprobarEntorno == 0:
		print("No se ha creado el entorno")
		sys.exit()
	print("monitor")
	print("==========================================")
	numeroMaquinas = len(glob.glob("cdps-vm_s*"))
	if numeroMaquinas == 0:
		print("No hay maquinas virtuales que monitorizar")
		sys.exit()
	salida = os.system("grep s1 aux.txt > var.txt")
	if salida != 0:
		print("No hay maquinas virtuales en funcionamiento que monitorizar")
		sys.exit()
	#Básico : estado
	if len(sys.argv) <3:
		for x in range(1,numeroMaquinas+1):
			salida = os.system("grep s"+str(x)+" aux.txt > var.txt")
			if salida == 0:
				print("Estado de s"+str(x)+ " -->")
				os.system("sudo virsh domstate s"+str(x))
			else:
				print("La maquina "+str(x)+" no esta iniciada")
		salida2 = os.system("grep lb aux.txt > var.txt")
		if salida2 == 0:
			print("Estado de lb -->")
			os.system("sudo virsh domstate lb")
		else:
			print("La maquina lb no esta iniciada")
		salida3 = os.system("grep c1 aux.txt > var.txt")
		if salida3 == 0:
			print("Estado de c1 -->")
			os.system("sudo virsh domstate c1")
		else:
			print("La maquina c1 no esta iniciada")
	#Info:
	elif sys.argv[2] == "-i":
		for x in range(1,numeroMaquinas+1):
			salida = os.system("grep s"+str(x)+" aux.txt > var.txt")
			if salida == 0:
				print("Informacion de s"+str(x)+ " -->")
				os.system("sudo virsh dominfo s"+str(x))
			else:
				print("La maquina s"+str(x)+" no esta iniciada")
		salida2 = os.system("grep lb aux.txt > var.txt")
		if salida2 == 0:
			print("Informacion de lb -->")
			os.system("sudo virsh dominfo lb")
		else:
			print("La maquina lb no esta iniciada")
		salida3 = os.system("grep c1 aux.txt > var.txt")
		if salida3 == 0:
			print("Informacion de c1 -->")
			os.system("sudo virsh dominfo c1")
		else:
			print("La maquina c1 no esta iniciada")
	#cpu-stats:
	elif sys.argv[2] == "-cpu":
		for x in range(1,numeroMaquinas+1):
			salida = os.system("grep s"+str(x)+" aux.txt > var.txt")
			print("Info CPU de s"+str(x)+ " -->")
			if salida == 0:
				os.system("sudo virsh cpu-stats s"+str(x))
			else:
				print("La maquina "+str(x)+" no esta iniciada")
		salida2 = os.system("grep lb aux.txt > var.txt")
		if salida2 == 0:
			print("Info CPU de lb -->")
			os.system("sudo virsh cpu-stats lb")
		else:
			print("La maquina lb no esta iniciada")
		salida3 = os.system("grep c1 aux.txt > var.txt")
		if salida3 == 0:
			print("Info CPU de c1 -->")
			os.system("sudo virsh cpu-stats c1")
		else:
			print("La maquina c1 no esta iniciada")
	elif sys.argv[2] == "-only":
		if(len(sys.argv) <4):
				print("Falta id maquina virtual: monitor -only <id>")
				sys.exit()
		#Basica: 
		if (len(sys.argv) <5):
			salida = os.system("grep "+sys.argv[3]+" aux.txt > var.txt")
			if salida == 0:
				print("Estado de "+sys.argv[3]+" -->")
				os.system("sudo virsh domstate " + sys.argv[3])
			else:
				print("La maquina "+sys.argv[3]+" no esta iniciada")
			#Info:
		elif sys.argv[4] == "-i":
			salida = os.system("grep "+sys.argv[3]+" aux.txt > var.txt")
			if salida == 0:
				print("Informacion de "+sys.argv[3]+ " -->")
				os.system("sudo virsh dominfo "+sys.argv[3])
			else:
				print("La maquina "+sys.argv[3]+" no esta iniciada")
		#cpu-stats:
		elif sys.argv[4] == "-cpu":
			salida = os.system("grep "+sys.argv[3]+" aux.txt > var.txt")
			if salida == 0:
				print("Info CPU de "+sys.argv[3]+ " -->")
				os.system("sudo virsh cpu-stats "+sys.argv[3])
			else:
				print("La maquina "+sys.argv[3]+" no esta iniciada")
		else:
			print("Las opciones son: -i, -cpu.")
	else:
		print("Las opciones son: -i, -cpu, -only .")

else: 
	print("MANUAL")
	print("Bienvenido al manual del P.E Script.\n")
	print("Estas son las siguientes funciones de las que dispone para administrar un enterno de balanceo de carga con servidores.\n")
	print("--> Create:\n inicia el entorno, crea los ficheros. Se determina el numero de servidores a crear mediante:\n")
	print("-f : desde fichero esterno.")
	print("-n : manualmente.\n")
	print("--> Start:\n inicia las maquinas virtuales y muestra sus consolas. Dos opciones de consola:\n")
	print("-g : consola grafica")
	print("-t : consola textual\n")
	print("--> Stop:\n para las maquinas virtuales y cierra sus consolas. Posibilidad de añadir:")
	print("-f: parada forzada\n")
	print("--> Destroy:\n terminar el entorno, parando las maquinas virtuales y elimando los ficheros asociados")
	print("--> Monitor:\n Monitoriza el entorno, aportardo información sobre todas las MV:\n")
	print("Sin aportar parametro, se proporciona el estado de la MV.")
	print("-cpu : Valores estadisticos sobre la CPU.\n")
	print("-i : Informacion basica del dominio.")
	print("-only: Permite obtener informacion individual de una MV proporcionando dominio de la MV y parametro de consulta.\n")
