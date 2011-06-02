
package org.ofbiz.common.test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.*;
import java.lang.*;

// an abstraction of an object that will allow you to call any method available at runtime
public class TestObject {

	private String className;
	private Object obj;

	public Object getObject() {
		return obj;
	}
	
	public void setObject(Object object) {
		obj = object;
	}

	// Set the class, don't create an instance
	public TestObject(String t) throws Exception {
		className = t;
		obj = null;
	}

	public TestObject(String t, Object o) throws Exception {
		className = t;
		obj = o;
	}

	private Method[] getMethods() throws Exception {
		Class type = Class.forName(className);
		return type.getDeclaredMethods();
	}

	private Constructor[] getConstructors() throws Exception {
		Class type = Class.forName(className);
		return type.getDeclaredConstructors();
	}

	private static Class getBoxedClass (Class primitive) {
		if (primitive == byte.class)
			return Byte.class;
		else if (primitive == short.class)
			return Short.class;
		else if (primitive == int.class)
			return Integer.class;
		else if (primitive == long.class)
			return Long.class;
		else if (primitive == float.class)
			return Float.class;
		else if (primitive == double.class)
			return Double.class;
		else if (primitive == boolean.class)
			return Boolean.class;
		else if (primitive == char.class)
			return Character.class;

		return null;
	}

	// handles primitives and null
	public static boolean isInstanceOf(Object data, Class cls) {
		if (cls.isPrimitive()) {
			if (data == null)
				return false;

			// if it casts to a boxed class then it will unbox to a primitive of the same type
			cls = getBoxedClass(cls);
		}

		// try to cast the data (null will always cast)
		try {
			cls.cast(data);
		} catch (ClassCastException e) {
			return false;
		}

		return true;
	}
	
	// doesn't handle variable length parameters
	public static List<Class[]> getMatches(List<Class[]> types, List<Object> dataArray) {
		List<Class[]> matches = new ArrayList<Class[]>();

		for (Class[] funcTypes : types) {

			if (funcTypes.length != dataArray.size())
				continue;

			boolean isMatch = true;

			for (int i = 0; i < funcTypes.length; i++) {
				Class type = funcTypes[i];
				Object data = dataArray.get(i);

				if (!isInstanceOf(data, type)) {
					isMatch = false;
					break;
				}
			}

			if (isMatch)
				matches.add(funcTypes);
		}

		return matches;
	}

	// does this handle primitives
	public static int compare(Class[] first, Class[] second) {
		int firstCount = 0;
		int secondCount = 0;

		// assign priority
		for (int i = 0; i < first.length; i++) {
			Class cls1 = first[i];
			Class cls2 = second[i];

			if (cls1.isPrimitive())
				cls1 = getBoxedClass(cls1);
			if (cls2.isPrimitive())
				cls2 = getBoxedClass(cls2);
			
			if (cls1 == cls2) {
				// do nothing
			} else {
				boolean canAssign1 = cls1.isAssignableFrom(cls2);
				boolean canAssign2 = cls2.isAssignableFrom(cls1);
				
				if (canAssign1) {
					firstCount = 1;
				} else {
					secondCount = -1;
				}
			}
		}

		return firstCount + secondCount;
		// Note: both totalPositive and totalNegative can never be 0 because they would be the same function
	}
	
	public static Class[] getClosestMatch(List<Class[]> types, List<Object> dataArray) throws Exception {
		List<Class[]> matches = getMatches(types, dataArray);

		if (matches.size() == 0)
			return null;
		else if (matches.size() == 1)
			return matches.get(0);

		Class[] bestMatch = matches.remove(0);
		boolean bestIsAmbigous = false;

		for (Class[] match : matches) {
			int i = compare(match, bestMatch);
			if (i == 0){
				bestIsAmbigous = true;				
			} else if (i > 1) {
				bestIsAmbigous = false;
				bestMatch = match;
			} else {
				// best is still the best (no change)
			}
		}

		if (bestIsAmbigous)
			return null;

		return bestMatch;
	}

	public TestObject newInstance(Object... data) throws Exception {
		TestObject newObj = new TestObject(className);

		List<Class[]> constructors = new ArrayList<Class[]>();
		List<Object> dataArray = new ArrayList<Object>();
		for (Constructor c : getConstructors()) {
			constructors.add(c.getParameterTypes());
		}
		for (Object d : data) {
			dataArray.add(d);
		}
		
		Class[] match = getClosestMatch(constructors, dataArray);
		if (match == null)
			throw new Exception ("Could not determine constructor");
		
		Class type = Class.forName(className);
		Constructor constructor = type.getDeclaredConstructor(match);
		constructor.setAccessible(true);
		newObj.setObject(constructor.newInstance(data));

		return newObj;
	}
	
	public Object call(String methodName, Object... data) throws Exception {
		List<Method> ms = new ArrayList<Method>();
		List<Class[]> methods = new ArrayList<Class[]>();
		List<Object> dataArray = new ArrayList<Object>();
		for (Method m : getMethods()) {
		 	if (m.getName().equals(methodName)) {
				methods.add(m.getParameterTypes());
				ms.add(m);
		 	}
		}
		for (Object d : data) {
			dataArray.add(d);
		}

		Class[] match = getClosestMatch(methods, dataArray);
		if (match == null)
			throw new Exception ("Could not determine method");

		Method method = ms.get(methods.indexOf(match));
		method.setAccessible(true);
		return method.invoke(obj, data);
	}
	
	public Object get(String fieldName) throws Exception {
		Class type = Class.forName(className);
		Field field = type.getDeclaredField(fieldName);
		field.setAccessible(true);
		return field.get(obj);
	}
	
	public void set(String fieldName, Object value) throws Exception {
		Class type = Class.forName(className);
		Field field = type.getDeclaredField(fieldName);
		field.setAccessible(true);
		field.set(obj, value);
	}
}