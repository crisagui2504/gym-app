' Lanza Gym Tracker sin mostrar ninguna ventana de consola.
' Doble clic = abre el dashboard directo en el navegador.
' Para detener el servidor: Administrador de tareas -> finalizar "python.exe".

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = carpeta

' 0 = ventana oculta ; False = no esperar a que termine
sh.Run """" & carpeta & "\GymTracker.bat""", 0, False
