from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import RegistrationSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status


@api_view(["POST"])
def register(request):
    serializer = RegistrationSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "User created successfully"}, status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response({"username": request.user.username, "email": request.user.email})
